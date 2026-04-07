# Postcard MAX Backend

Основной backend для чат-бота открыток в MAX.

Что внутри:

- `FastAPI` для webhook и внутреннего API
- `Celery + Redis` для фоновой генерации
- `PostgreSQL` для данных
- `S3-compatible storage` для хранения картинок
- адаптеры под `MAX API` и image provider
- `Alembic` для миграций схемы
- rate limiting и blocklist-модерация
- operational scripts для webhook, polling и диагностики

## Запуск

1. Скопируйте `.env.example` в `.env` и заполните токены.
2. Backend при старте сам выполнит Alembic migrations.
3. Для локального запуска всего продукта рядом должен лежать frontend-репозиторий `postcard_max_frontend`.
4. Из корня backend-репозитория выполните `docker compose -f docker-compose.workspace.yml up --build`.
5. Backend будет доступен на `http://localhost:8000`.

## Health endpoints

- `GET /api/v1/health`
- `GET /api/v1/health/ready`

## Internal API

- `GET /api/v1/internal/summary`
- `GET /api/v1/internal/users`
- `GET /api/v1/internal/users/{id}`
- `GET /api/v1/internal/prompts`
- `GET /api/v1/internal/prompts/{id}`
- `GET /api/v1/internal/generations`
- `GET /api/v1/internal/generations/{id}`
- `GET /api/v1/internal/generations/{id}/image`
- `GET /api/v1/internal/errors`
- `GET /api/v1/internal/exports/users.csv`
- `GET /api/v1/internal/exports/prompts.csv`
- `GET /api/v1/internal/exports/generations.csv`

## Регистрация webhook в MAX

После заполнения `MAX_BOT_TOKEN`, `MAX_BOT_SECRET` и `BASE_WEBHOOK_URL` можно зарегистрировать webhook командой:

```bash
python -m postcard_backend.scripts.register_webhook
```

## Ручной запуск миграций

```bash
python -m postcard_backend.scripts.migrate
```

## Полезные скрипты

```bash
python -m postcard_backend.scripts.get_me
python -m postcard_backend.scripts.list_subscriptions
python -m postcard_backend.scripts.delete_webhook
python -m postcard_backend.scripts.poll_updates
```

`poll_updates` полезен для локальной разработки, когда webhook еще не выведен наружу.

## Проверки в CI

```bash
pip install ".[dev]"
ruff check src tests
pytest
```

## Документация

Этот репозиторий является основной точкой входа в проект. Здесь лежат backend, общая документация и deploy-файлы для всего продукта.

- [Техническое задание](docs/TZ.md)
- [Архитектура](docs/ARCHITECTURE.md)
- [Конфигурация](docs/CONFIGURATION.md)
- [Деплой](docs/DEPLOY.md)
- [Git Setup](docs/GIT_SETUP.md)
- [Deploy folder](deploy/README.md)
- [Workspace compose](docker-compose.workspace.yml)

Если смотреть проект на GitHub, для понимания всей системы достаточно открыть этот репозиторий.
