def welcome_message(bot_name: str) -> str:
    return (
        f"Привет! Я {bot_name}. Пришли тему для открытки, например: "
        "весеннее настроение, день рождения для друга, уютный зимний вечер, ретро-путешествие."
    )


def help_message(bot_name: str) -> str:
    return (
        f"{bot_name} умеет генерировать открытки по теме.\n"
        "1. Отправь тему одним сообщением.\n"
        "2. Дождись результата.\n"
        "3. Нажми «Еще вариант», если хочешь другую версию.\n"
        "Совет: лучше короткие и конкретные темы."
    )


def rate_limit_message(retry_after_seconds: int | None) -> str:
    if retry_after_seconds:
        return (
            "Слишком много запросов за короткое время. "
            f"Подожди примерно {retry_after_seconds} сек. и попробуй снова."
        )
    return "Слишком много запросов за короткое время. Немного подожди и попробуй снова."


def active_generation_message() -> str:
    return "У тебя уже есть активная генерация открытки. Дождись результата и потом отправь новую тему."


def generation_started_message(topic: str) -> str:
    return f"Генерирую открытку по теме: {topic[:180]}"


def generation_ready_message(topic: str) -> str:
    return f"Готово. Тема: {topic[:180]}"


def generation_failed_message() -> str:
    return "Не получилось сгенерировать открытку. Попробуй немного изменить тему и отправить ее еще раз."


def blocked_prompt_message() -> str:
    return "Эта тема заблокирована правилами безопасности. Попробуй другую тему для открытки."


def invalid_prompt_message() -> str:
    return "Пришли текстовую тему для открытки."


def callback_more_variation_message() -> str:
    return "Генерирую еще один вариант."


def callback_new_theme_message() -> str:
    return "Пришли новую тему одним сообщением."


def callback_unknown_message() -> str:
    return "Неизвестное действие."


def callback_missing_prompt_message() -> str:
    return "Исходный запрос не найден."
