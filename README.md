# Todo Clean Architecture Demo (Citus)

Проект переведен на Citus:
- шардирование делает `create_distributed_table('todos', 'id')`;
- репликация шардов задается параметром `citus.shard_replication_factor`.

## Запуск

```bash
docker compose down -v
docker compose up --build
```

API: `http://localhost:8888`  
Citus coordinator: `localhost:5432`

## Что теперь делает приложение

- подключается только к coordinator (`DATABASE_URL`);
- при старте:
1. создает таблицы SQLAlchemy;
2. регистрирует worker-узлы в Citus (`citus_add_node`);
3. выставляет `citus.shard_count` и `citus.shard_replication_factor`;
4. делает таблицу `todos` distributed.

## Переменные окружения

Смотри [.env.example](/C:/Users/ivane/todo-project/.env.example).

Ключевые:
- `DATABASE_URL`
- `CITUS_INTER_NODE_PASSWORD`
- `CITUS_WORKER_NODES`
- `CITUS_SHARD_COUNT`
- `CITUS_SHARD_REPLICATION_FACTOR`

`CITUS_INTER_NODE_PASSWORD` нужен для подключений coordinator -> worker.
Если не задан, используется `POSTGRES_PASSWORD`.
