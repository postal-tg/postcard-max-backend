# Configuration

Ниже то, что будет максимально похоже на ваши привычные `bot_config.py`, только у нас источником правды остается `.env`, а Python-конфиг собирается из него.

## Backend

Главные параметры backend лежат в:

- [config.py](../src/postcard_backend/core/config.py)
- [bot_config.py](../src/postcard_backend/core/bot_config.py)
- [.env.example](../.env.example)
- [migrate.py](../src/postcard_backend/scripts/migrate.py)

Для локальной разработки без публичного webhook можно использовать:

- [poll_updates.py](../src/postcard_backend/scripts/poll_updates.py)

Аналогия с вашими старыми проектами:

- `BOT_TOKEN_WEBHOOK` -> `MAX_BOT_TOKEN`
- `BOT_NAME` -> `MAX_BOT_NAME`
- `BOT_LINK` -> `MAX_BOT_PUBLIC_LINK`
- `SERVER_URL` -> `SERVER_URL`
- `WEBHOOK_PATH` -> `WEBHOOK_PATH`
- `BASE_WEBHOOK_URL` -> `BASE_WEBHOOK_URL`
- `update_types` webhook-подписки -> `MAX_WEBHOOK_UPDATE_TYPES`
- `WEB_SERVER_HOST` -> `WEB_SERVER_HOST`
- `WEB_SERVER_PORT` -> `WEB_SERVER_PORT`
- `RATE_LIMITER_CAPACITY` -> `RATE_LIMITER_CAPACITY`
- `RATE_LIMITER_PERIOD` -> `RATE_LIMITER_PERIOD`
- `MAX_MESSAGE_TEXT_LENGTH` -> `MAX_MESSAGE_TEXT_LIMIT`
- `content moderation allow/deny list` -> `PROMPT_BLOCKLIST`

## Что нужно заполнить тебе

Перед первым реальным запуском потребуются:

- `MAX_BOT_TOKEN`
- `MAX_BOT_SECRET`
- `MAX_BOT_NAME`
- `MAX_BOT_PUBLIC_LINK`
- `BASE_WEBHOOK_URL`
- `INTERNAL_API_KEY`
- `OPENAI_API_KEY` или другой ключ провайдера, если решим переключиться

Если будет production storage, еще нужны:

- `STORAGE_ENDPOINT_URL`
- `STORAGE_PUBLIC_BASE_URL`
- `STORAGE_ACCESS_KEY`
- `STORAGE_SECRET_KEY`

## Откуда брать каждое значение

### Из вашей инфраструктуры MAX

- `MAX_BOT_TOKEN` - токен уже созданного бота в вашей организации
- `MAX_BOT_NAME` - имя бота, например `@postcard_bot`
- `MAX_BOT_PUBLIC_LINK` - публичная ссылка на бота
- webhook-параметры - домен, путь и доступ к подпискам

Если у тебя нет прямого доступа к панели или организационному контуру `MAX`, эти значения нужно запросить у наставника или у коллеги, который ведет бота.

По официальной документации `MAX`, платформа партнеров доступна для юрлиц и ИП, которые являются резидентами РФ. Значит для российской организации это реальный путь, если бот уже создан или у команды есть доступ к профилю организации.

### Из OpenAI

- `OPENAI_API_KEY`

Как получить:

1. Открыть `https://platform.openai.com/`
2. Перейти в `API keys`
3. Нажать `Create new secret key`
4. Скопировать ключ в `.env`

Важно: по официальному списку поддерживаемых стран OpenAI API Россия не указана. Это означает, что прямой запуск через `OpenAI` для пользователя или команды только с российским контуром может быть недоступен. Если у вашей организации нет уже существующего поддерживаемого аккаунта и биллинга, лучше заранее закладывать альтернативного image provider.

### Сгенерировать самостоятельно

- `MAX_BOT_SECRET`
- `INTERNAL_API_KEY`
- `FRONTEND_SECRET_KEY`
- `ADMIN_PASSWORD`

Пример команды:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Для `ADMIN_PASSWORD` лучше использовать отдельное значение, а не тот же самый секрет.

## Что можно заполнить уже сейчас

Даже без доступов к `MAX` ты можешь заранее заполнить:

- `MAX_BOT_SECRET`
- `INTERNAL_API_KEY`
- `OPENAI_API_KEY`
- `FRONTEND_SECRET_KEY`
- `ADMIN_USERNAME`
- `ADMIN_PASSWORD`

А позже, когда команда даст боевые значения, добавить:

- `MAX_BOT_TOKEN`
- `MAX_BOT_NAME`
- `MAX_BOT_PUBLIC_LINK`
- `BASE_WEBHOOK_URL`

## Пример минимального backend `.env`

```env
MAX_BOT_TOKEN=replace-me-from-max
MAX_BOT_SECRET=generated-random-secret
MAX_BOT_NAME=@postcard_bot
MAX_BOT_PUBLIC_LINK=https://max.ru/postcard_bot
BASE_WEBHOOK_URL=https://bot.example.com
INTERNAL_API_KEY=generated-internal-api-key
OPENAI_API_KEY=sk-...
```

## Пример минимального frontend `.env`

```env
INTERNAL_API_KEY=generated-internal-api-key
FRONTEND_SECRET_KEY=generated-frontend-secret
ADMIN_USERNAME=admin
ADMIN_PASSWORD=strong-password
```

## Полезные ссылки

Внутренние ссылки:

- [backend `.env.example`](../.env.example)
- [frontend `.env.example`](https://github.com/postal-tg/postcard-max-frontend/blob/main/.env.example)
- [backend config](../src/postcard_backend/core/config.py)
- [backend bot config](../src/postcard_backend/core/bot_config.py)
- [backend migrate script](../src/postcard_backend/scripts/migrate.py)
- [poll updates script](../src/postcard_backend/scripts/poll_updates.py)

Официальные внешние ссылки:

- MAX docs: https://dev.max.ru/docs
- MAX API overview: https://dev.max.ru/docs-api
- OpenAI API keys: https://platform.openai.com/api-keys
- OpenAI supported countries: https://help.openai.com/en/articles/5347006-openai-api-supported-countries-and-territories

## Какой у нас подход

- чувствительные данные храним в `.env`
- типизированный runtime-конфиг собираем в Python
- значения лимитов не размазываем по коду
- под MAX сразу держим ограничение `MAX_MESSAGE_TEXT_LIMIT=4000`
- для пользовательской темы держим отдельный продуктовый лимит `PROMPT_TEXT_LIMIT`
- миграции БД прогоняются через `Alembic`
