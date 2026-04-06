from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Postcard MAX Backend"
    environment: str = "development"
    api_v1_prefix: str = "/api/v1"

    database_url: str = "postgresql+psycopg://postcard:postcard@localhost:5432/postcard_bot"
    redis_url: str = "redis://localhost:6379/0"

    max_api_base_url: str = "https://platform-api.max.ru"
    max_bot_token: str = ""
    max_bot_secret: str = ""
    max_bot_name: str = "@postcard_bot"
    max_bot_public_link: str = "https://max.ru/postcard_bot"
    server_url: str = "http://localhost:8000"
    webhook_path: str = "/api/v1/max/webhook"
    base_webhook_url: str = "https://example.com"
    max_webhook_update_types: str = "message_created,message_callback,bot_started"
    web_server_host: str = "0.0.0.0"
    web_server_port: int = 8000
    internal_api_key: str = "change-me"

    prompt_text_limit: int = 1000
    max_message_text_limit: int = 4000
    max_active_generations_per_user: int = 1
    rate_limiter_capacity: int = 30
    rate_limiter_period: int = 60
    prompt_blocklist: str = "nsfw,nude,porn,sex,explicit,gore,blood,violence"

    image_provider: str = "openai"
    openai_api_key: str = ""
    openai_image_model: str = "gpt-image-1-mini"
    openai_image_size: str = "1024x1024"
    openai_image_quality: str = "medium"

    storage_bucket: str = "postcards"
    storage_endpoint_url: str = "http://localhost:9000"
    storage_public_base_url: str = "http://localhost:9000"
    storage_access_key: str = "minioadmin"
    storage_secret_key: str = "minioadmin"
    storage_region: str = "us-east-1"
    storage_use_ssl: bool = False

    generation_retry_attempts: int = 4
    generation_retry_backoff_seconds: int = 3

    postcard_style_preamble: str = Field(
        default=(
            "Create a polished messenger-friendly greeting postcard illustration. "
            "Keep one clear subject, cinematic composition, strong visual storytelling, "
            "no typography inside the image, bright but tasteful colors, clean details."
        )
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
