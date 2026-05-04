# Todo API + LLM Worker (RabbitMQ)

This project now consists of two microservices:

- `load-balancer`: Nginx reverse proxy in front of the API with request and connection limits.
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
- Nginx (`load-balancer`) for load balancing and basic DDoS/spam protection
- Fail2ban (`fail2ban`) for temporary IP bans after repeated Nginx limit violations
- Prometheus (`prometheus`) and Nginx exporter (`nginx-exporter`) for load
  balancing metrics
- Grafana (`grafana`) for dashboard visualization

## Run

```bash
docker compose down -v
docker compose up --build
```

The compose file starts two API replicas by default. To experiment with a
different number of replicas, override it from the command line:

```bash
docker compose up --build --scale api=3
```

Endpoints:

- API through Nginx: `http://localhost:8888`
- RabbitMQ UI: `http://localhost:15672` (credentials from `.env`)
- Swagger UI: `http://localhost:8888/docs`
- Prometheus UI: `http://localhost:9090`
- Grafana UI: `http://localhost:3000` (`admin` / `admin` by default)
- Nginx exporter metrics: `http://localhost:9113/metrics`

The API container is no longer published directly on the host. Inside the Docker
network Nginx sends traffic to `api:8000` and distributes requests across API
replicas when `--scale api=N` is used.

## Load balancer and anti-spam limits

Nginx is configured in `nginx/nginx.conf`:

- `least_conn` load balancing across API replicas.
- General API limit: `10` requests per second per client IP with a short burst.
- Auth endpoints limit: `3` requests per second per client IP to slow password
  guessing and registration spam.
- Per-IP connection limits, `1 MB` request body limit, and short request
  timeouts to reduce the impact of noisy clients.
- When a client exceeds the limits, Nginx returns `429 Too Many Requests`.
- Fail2ban watches `nginx/logs/error.log`. If one IP triggers Nginx request or
  connection limits `5` times within `60` seconds, it is banned for `300`
  seconds.
- Nginx and Fail2ban use `LOG_TZ=UTC` by default, so Fail2ban interprets Nginx
  log timestamps without timezone drift.

This is intentionally demo-friendly protection. In production, put the service
behind a cloud DDoS provider or WAF as well, because large network-layer attacks
must be absorbed before traffic reaches the Docker host.

## Load balancing metrics

Prometheus is configured in `prometheus/prometheus.yml`.
Grafana is provisioned from `grafana/provisioning` and includes the
`Load Balancing Demo` dashboard.

Useful demo queries:

- Nginx active connections:
  `nginx_connections_active`
- Nginx accepted/handled requests:
  `rate(nginx_http_requests_total[1m])`
- Requests per API replica:
  `sum by (instance) (rate(todo_api_http_requests_total[1m]))`
- Request latency per API replica:
  `histogram_quantile(0.95, sum by (le, instance) (rate(todo_api_http_request_duration_seconds_bucket[1m])))`

For the balancing demo, generate traffic through `http://localhost:8888`, then
open Prometheus and compare the `instance` labels for `api-replicas`.

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
