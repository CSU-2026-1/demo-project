from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@citus-coordinator:5432/postgres",
)
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "")
CITUS_COORDINATOR_HOST = os.getenv("CITUS_COORDINATOR_HOST", "citus-coordinator")
CITUS_COORDINATOR_PORT = int(os.getenv("CITUS_COORDINATOR_PORT", "5432"))
CITUS_WORKER_NODES = os.getenv("CITUS_WORKER_NODES", "citus-worker-1:5432,citus-worker-2:5432")
# Количество логических шардов distributed-таблицы (влияет на параллелизм и балансировку данных).
CITUS_SHARD_COUNT = int(os.getenv("CITUS_SHARD_COUNT", "8"))
# Сколько копий каждого шарда хранить на разных worker-нодах (отказоустойчивость/чтение).
CITUS_SHARD_REPLICATION_FACTOR = int(os.getenv("CITUS_SHARD_REPLICATION_FACTOR", "2"))
CITUS_INTER_NODE_PASSWORD = os.getenv("CITUS_INTER_NODE_PASSWORD", POSTGRES_PASSWORD)


@dataclass(frozen=True)
class WorkerNode:
    host: str
    port: int


def _parse_worker_nodes(raw_value: str) -> list[WorkerNode]:
    nodes: list[WorkerNode] = []
    for item in raw_value.split(","):
        item = item.strip()
        if not item:
            continue
        host, port_text = item.split(":")
        nodes.append(WorkerNode(host=host.strip(), port=int(port_text.strip())))
    return nodes


engine = create_async_engine(DATABASE_URL, echo=False, pool_pre_ping=True)
SessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    autoflush=False,
    expire_on_commit=False,
)
Base = declarative_base()


async def init_citus_for_todos_table() -> None:
    # Базовая валидация параметров кластера, чтобы не стартовать с некорректной конфигурацией.
    if CITUS_SHARD_COUNT < 1:
        raise RuntimeError("CITUS_SHARD_COUNT must be >= 1")
    if CITUS_SHARD_REPLICATION_FACTOR < 1:
        raise RuntimeError("CITUS_SHARD_REPLICATION_FACTOR must be >= 1")

    # Разбираем список worker-нод из env в формате "host:port,host:port".
    worker_nodes = _parse_worker_nodes(CITUS_WORKER_NODES)
    if not worker_nodes:
        raise RuntimeError("CITUS_WORKER_NODES must contain at least one worker node")
    if not CITUS_INTER_NODE_PASSWORD:
        raise RuntimeError("CITUS_INTER_NODE_PASSWORD (or POSTGRES_PASSWORD) must be set")

    async with engine.begin() as conn:
        # Включаем расширение Citus в БД coordinator (идемпотентно).
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS citus"))
        # Сохраняем пароль для внутренних подключений coordinator -> worker.
        await conn.execute(
            text(
                "INSERT INTO pg_dist_authinfo (nodeid, rolename, authinfo) "
                "VALUES (0, current_user, :authinfo) "
                "ON CONFLICT (nodeid, rolename) DO UPDATE SET authinfo = EXCLUDED.authinfo"
            ),
            {"authinfo": f"password={CITUS_INTER_NODE_PASSWORD}"},
        )
        # Сообщаем Citus, как worker-ноды должны обращаться к coordinator.
        await conn.execute(
            text("SELECT citus_set_coordinator_host(:host, :port)"),
            {"host": CITUS_COORDINATOR_HOST, "port": CITUS_COORDINATOR_PORT},
        )

        # Регистрируем worker-ноды в метаданных Citus (только если еще не добавлены).
        for node in worker_nodes:
            node_exists = await conn.scalar(
                text(
                    "SELECT 1 FROM pg_dist_node "
                    "WHERE nodename = :host AND nodeport = :port LIMIT 1"
                ),
                {"host": node.host, "port": node.port},
            )
            if not node_exists:
                await conn.execute(
                    text("SELECT citus_add_node(:host, :port)"),
                    {"host": node.host, "port": node.port},
                )

        # Сессионные настройки Citus для дальнейшего create_distributed_table.
        await conn.execute(text(f"SET citus.shard_count TO {CITUS_SHARD_COUNT}"))
        await conn.execute(
            text(f"SET citus.shard_replication_factor TO {CITUS_SHARD_REPLICATION_FACTOR}")
        )

        # Превращаем таблицу в distributed только один раз (безопасно при повторных стартах).
        is_distributed = await conn.scalar(
            text("SELECT 1 FROM pg_dist_partition WHERE logicalrelid = 'public.todos'::regclass")
        )
        if not is_distributed:
            await conn.execute(
                text(
                    "SELECT create_distributed_table("
                    "'public.todos', 'id', colocate_with => 'none'"
                    ")"
                )
            )
