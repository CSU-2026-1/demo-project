# Todo Clean Architecture Demo

Минимальный пример FastAPI-проекта с `dependency_injector`, разделенный на слои:

- API (`app/api`) — только HTTP-ручки.
- Сервисы (`app/services`) — бизнес-логика.
- Репозитории (`app/repositories`) — работа с данными (сейчас InMemory).
- Контейнер (`app/containers`) — настройка DI.

## Установка и запуск

### Docker Compose
```bash
docker compose up --build
```
API будет на http://localhost:8000, Postgres на порту 5432.

Переменные окружения лежат в `.env` (локальный, игнорируется git), пример — `.env.example`.

## Маршруты
- `POST /todos/` — создать задачу.
- `GET /todos/` — список.
- `GET /todos/{id}` — получить по id.
- `PUT /todos/{id}` — обновить частично/полностью.
- `DELETE /todos/{id}` — удалить.
