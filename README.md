# Todo API + LLM Worker (RabbitMQ)

This project now consists of two microservices:

- `api`: FastAPI service for CRUD on todos.
- `worker`: background service that receives created todos from RabbitMQ, calls the LLM, and stores generated implementation steps in DB.

## Service layout

- `api` service:
  - source: `./app`
  - image build: root `./Dockerfile`
  - dependencies: root `./requirements.txt`
- `worker` service:
  - source: `./worker`
  - image build: `./worker/Dockerfile`
  - dependencies: `./worker/requirements.txt`

Infrastructure:

- PostgreSQL + Citus cluster (`citus-coordinator`, `citus-worker-1`, `citus-worker-2`)
- RabbitMQ (`rabbitmq`)
- Redis (`redis`) for API caching

## Run

```bash
docker compose down -v
docker compose up --build
```

Endpoints:

- API: `http://localhost:8888`
- RabbitMQ UI: `http://localhost:15672` (credentials from `.env`)

## Message flow

1. API creates todo in `todos`.
2. API publishes message to queue `TODO_QUEUE_NAME` with payload:
   - `todo_id`
   - `title`
3. Worker consumes the message, calls LLM, and writes steps to `todo_steps`.
4. Worker invalidates Redis cache for this todo.
5. API `GET /todos` and `GET /todos/{id}` returns cached data when available and refreshes cache on DB read.

## Environment variables

See `.env.example`.

Important variables:

- `RABBITMQ_URL`
- `REDIS_URL`
- `TODO_QUEUE_NAME`
- `TODO_CACHE_TTL_SECONDS`
- `TODO_CACHE_KEY_PREFIX`
- `YANDEX_CLOUD_API_KEY`
- `YANDEX_CLOUD_FOLDER`
- `OPENAI_PROMPT_ID`
