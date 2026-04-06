from fastapi import FastAPI

from postcard_backend.api.router import router
from postcard_backend.core.config import get_settings
from postcard_backend.core.logging import configure_logging
from postcard_backend.services.storage import ObjectStorage

settings = get_settings()
configure_logging()

app = FastAPI(title=settings.app_name)
app.include_router(router, prefix=settings.api_v1_prefix)


@app.on_event("startup")
def startup() -> None:
    ObjectStorage(settings).ensure_bucket()
