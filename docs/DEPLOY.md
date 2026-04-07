# Deploy Notes

## Что нужно до деплоя

Нужны:

- сервер с Linux или другой средой, где есть `Docker` и `Docker Compose`
- домен для backend, например `bot.example.com`
- домен для frontend, например `admin.example.com`
- доступ к DNS, чтобы направить домены на сервер
- заполненные `.env` для backend и frontend
- ключ `OPENAI_API_KEY`
- данные бота `MAX`, если нужен реальный запуск

Без `MAX_BOT_TOKEN` и связанных с ним значений можно поднять инфраструктуру и проверить health endpoints, но нельзя полноценно подключить бота.

Практический комментарий по РФ:

- `MAX` для российских юрлиц и ИП - реалистичный сценарий, если ваша организация уже подключена к платформе партнеров
- `OpenAI API` может быть организационным блокером, потому что Россия не указана в официальном списке поддерживаемых стран
- если у команды уже есть рабочий корпоративный аккаунт и биллинг в поддерживаемой юрисдикции, можно оставаться на `OpenAI`
- если такого доступа нет, лучше переключить backend на альтернативного провайдера, доступного вашей организации

## Что важно для MAX

- webhook должен быть доступен по `HTTPS`
- для production удобнее держать его на `443`
- нужен валидный TLS-сертификат
- backend должен отвечать `200 OK` достаточно быстро

По документации MAX:

- webhook работает по `HTTPS`
- поддерживаются порты `80`, `8080`, `443`, `8443` и диапазон `16384-32383`
- при ошибках доставки MAX делает повторные попытки
- если долго нет успешных ответов, подписка может быть снята

## Простейшая схема деплоя

1. Сервер с Docker и Docker Compose.
2. `postgres`, `redis`, `minio`, `backend-api`, `backend-worker`, `frontend`.
3. Reverse proxy перед контейнерами.
4. Отдельный домен для backend webhook и отдельный домен для админки.

Примечание:

- для работы админки не нужно открывать MinIO наружу, просмотр сгенерированных изображений идет через proxy-ручку frontend/backend

Пример:

- `bot.example.com` -> backend
- `admin.example.com` -> frontend

Шаблон reverse proxy лежит в:

- [Caddyfile.example](../deploy/Caddyfile.example)
- [Caddyfile.staging.example](../deploy/Caddyfile.staging.example)

Готовый staging/prod-like compose лежит в:

- [docker-compose.staging.yml](../deploy/docker-compose.staging.yml)
- [deploy README](../deploy/README.md)

## Что подготовить на машине или сервере

1. Клонировать оба репозитория или загрузить их на сервер.
2. Убедиться, что структура папок такая:

```text
parent-folder/
  postcard_max_backend/
  postcard_max_frontend/
```

3. Подготовить файлы окружения:

```powershell
Copy-Item ..\.env.example ..\.env
Copy-Item ..\..\postcard_max_frontend\.env.example ..\..\postcard_max_frontend\.env
Copy-Item .\.env.staging.example .\.env
Copy-Item .\Caddyfile.staging.example .\Caddyfile
```

## Что заполнить в файлах

### `postcard_max_backend/.env`

Минимум:

- `MAX_BOT_TOKEN`
- `MAX_BOT_SECRET`
- `MAX_BOT_NAME`
- `MAX_BOT_PUBLIC_LINK`
- `BASE_WEBHOOK_URL`
- `INTERNAL_API_KEY`
- `OPENAI_API_KEY`

### `postcard_max_frontend/.env`

Минимум:

- `INTERNAL_API_KEY`
- `FRONTEND_SECRET_KEY`
- `ADMIN_USERNAME`
- `ADMIN_PASSWORD`

### `deploy/.env`

Минимум:

- `POSTGRES_DB`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `MINIO_ROOT_USER`
- `MINIO_ROOT_PASSWORD`
- `BACKEND_DOMAIN`
- `FRONTEND_DOMAIN`

## Пошаговый локальный прогон перед сервером

Если хочешь сначала проверить, что стек вообще собирается:

1. Из корня backend-репозитория выполнить:

```powershell
docker compose -f docker-compose.workspace.yml up --build
```

2. Дождаться, пока поднимутся `postgres`, `redis`, `minio`, `backend-api`, `backend-worker`, `frontend`.
3. Проверить:

```text
http://localhost:8000/api/v1/health
http://localhost:8000/api/v1/health/ready
http://localhost:8001/health
http://localhost:8001
```

4. Если webhook еще не готов, использовать polling:

```powershell
python -m postcard_backend.scripts.poll_updates
```

## Рекомендуемый rollout на staging или production

1. Заполнить `postcard_max_backend/.env`.
2. Заполнить `postcard_max_frontend/.env`.
3. В папке `deploy` создать `.env` из шаблона `.env.staging.example`.
4. В папке `deploy` создать `Caddyfile` из `Caddyfile.staging.example`.
5. Проверить, что DNS backend и frontend уже указывают на сервер.
6. Поднять стек командой:

```powershell
cd deploy
docker compose -f docker-compose.staging.yml --env-file .env up -d --build
```

7. Проверить backend:

```text
https://<backend-domain>/api/v1/health
https://<backend-domain>/api/v1/health/ready
```

8. Проверить frontend:

```text
https://<frontend-domain>/health
https://<frontend-domain>/
```

9. Зарегистрировать webhook:

```powershell
cd ..
python -m postcard_backend.scripts.register_webhook
```

10. При необходимости посмотреть текущие подписки:

```powershell
python -m postcard_backend.scripts.list_subscriptions
```

11. Протестировать:

- `/start`
- обычную тему открытки
- callback `Еще вариант`
- callback `Новая тема`
- блокировку слишком длинной темы
- блокировку темы из blocklist
- запись событий в админку

## Что делать, если нет доступа к MAX

Если у тебя нет `MAX_BOT_TOKEN` и доступа к организационному контуру:

- можно подготовить `.env`
- можно поднять backend, frontend, Postgres, Redis и MinIO
- можно проверить health endpoints и логин в админку
- нельзя зарегистрировать живой webhook
- нельзя полностью пройти пользовательский сценарий в `MAX`

В этом случае проект остается в состоянии `deploy-ready`, но не `integration-verified`.

## Полезные ссылки

Внутренние ссылки:

- [backend README](../README.md)
- [Техническое задание](TZ.md)
- [Конфигурация](CONFIGURATION.md)
- [deploy compose](../deploy/docker-compose.staging.yml)
- [deploy env example](../deploy/.env.staging.example)
- [deploy caddy example](../deploy/Caddyfile.staging.example)
- [backend register webhook script](../src/postcard_backend/scripts/register_webhook.py)
- [backend list subscriptions script](../src/postcard_backend/scripts/list_subscriptions.py)

Официальные внешние ссылки:

- MAX docs: https://dev.max.ru/docs
- MAX API overview: https://dev.max.ru/docs-api
- MAX subscriptions: https://dev.max.ru/docs-api/methods/POST/subscriptions
- MAX messages: https://dev.max.ru/docs-api/methods/POST/messages
- MAX uploads: https://dev.max.ru/docs-api/methods/POST/uploads
- MAX callback answers: https://dev.max.ru/docs-api/methods/POST/answers
- OpenAI API keys: https://platform.openai.com/api-keys
- OpenAI supported countries: https://help.openai.com/en/articles/5347006-openai-api-supported-countries-and-territories
