# Architecture

## Backend

- `FastAPI` принимает webhook от `MAX`
- событие сохраняется в `webhook_events`
- фоновая задача `Celery` разбирает update
- rate limiter режет флуд до постановки тяжелых задач
- plain-text промпт валидируется и нормализуется
- блок-лист тем отсекает небезопасные запросы
- создаются `prompts` и `generation_requests`
- image provider генерирует картинку
- картинка кладется в `S3-compatible storage`
- backend загружает файл в `MAX` и отправляет сообщение пользователю
- схема БД фиксируется через `Alembic`

## Frontend

- отдельный Python frontend на `FastAPI + Jinja2`
- логин через cookie session
- данные читаются из backend internal API
- свои доменные данные frontend не хранит

## Data flow

1. Пользователь отправляет тему в MAX.
2. MAX дергает webhook backend.
3. Backend быстро отвечает `200` и ставит событие в очередь.
4. Worker валидирует plain text и запускает генерацию.
5. Итоговая открытка сохраняется в storage и отправляется обратно в MAX.
6. Frontend показывает статистику и историю через internal API.
