# Git Setup

Сейчас оба проекта уже инициализированы как отдельные локальные git-репозитории:

- `postcard_max_backend`
- `postcard_max_frontend`

## Что осталось сделать

1. Создать два пустых remote-репозитория в GitHub или GitLab.
2. Привязать `origin` в каждой папке.
3. Отправить `main`.

## Пример для backend

```bash
cd postcard_max_backend
git remote add origin <BACKEND_REMOTE_URL>
git push -u origin main
```

## Пример для frontend

```bash
cd postcard_max_frontend
git remote add origin <FRONTEND_REMOTE_URL>
git push -u origin main
```

## Что уже сделано

- в обеих папках есть `.git`
- созданы initial commits
- подготовлены `.gitignore`
- добавлены CI workflow-файлы
