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
- Swagger UI: `http://localhost:8888/docs`

## Auth

The API has local JWT authentication for classroom demos:

1. Register a user with `POST /auth/register`:

```json
{
  "username": "student",
  "password": "student-password"
}
```

2. Get a token with `POST /auth/token` using form fields `username` and `password`.
3. Send the token as `Authorization: Bearer <token>` when calling `/todos`.

In Swagger UI, use the `Authorize` button after requesting `/auth/token`.

Users registered with `POST /auth/register` get role `user`. For RBAC demos,
`POST /auth/register-admin` creates an `admin` user. Only `admin` can call
`DELETE /todos/{id}`; regular users receive `403 Forbidden`.

Tokens use `JWT_SECRET_KEY`, `JWT_ALGORITHM=HS256`, and
`JWT_ACCESS_TOKEN_EXPIRE_MINUTES`.

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
- `JWT_SECRET_KEY`
- `JWT_ACCESS_TOKEN_EXPIRE_MINUTES`
- `YANDEX_CLOUD_API_KEY`
- `YANDEX_CLOUD_FOLDER`
- `OPENAI_PROMPT_ID`
