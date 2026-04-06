import base64
from abc import ABC, abstractmethod
from dataclasses import dataclass
from io import BytesIO

from openai import OpenAI
from PIL import Image

from postcard_backend.core.config import Settings


@dataclass
class GeneratedImage:
    content: bytes
    content_type: str
    provider_name: str
    model: str
    estimated_cost_usd: float | None
    payload: dict


class ImageProvider(ABC):
    @abstractmethod
    def generate(self, prompt: str) -> GeneratedImage:
        raise NotImplementedError


class DummyImageProvider(ImageProvider):
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def generate(self, prompt: str) -> GeneratedImage:
        image = Image.new("RGB", (1024, 1024), color=(245, 182, 66))
        buffer = BytesIO()
        image.save(buffer, format="PNG")
        return GeneratedImage(
            content=buffer.getvalue(),
            content_type="image/png",
            provider_name="dummy",
            model="local-preview",
            estimated_cost_usd=0.0,
            payload={"prompt_preview": prompt[:200]},
        )


class OpenAIImageProvider(ImageProvider):
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.client = OpenAI(api_key=settings.openai_api_key)

    def generate(self, prompt: str) -> GeneratedImage:
        response = self.client.images.generate(
            model=self.settings.openai_image_model,
            prompt=prompt,
            size=self.settings.openai_image_size,
            quality=self.settings.openai_image_quality,
        )
        image_payload = response.data[0]
        image_bytes = base64.b64decode(image_payload.b64_json)
        estimated_cost = 0.011 if self.settings.openai_image_quality == "medium" else 0.005
        return GeneratedImage(
            content=image_bytes,
            content_type="image/png",
            provider_name="openai",
            model=self.settings.openai_image_model,
            estimated_cost_usd=estimated_cost,
            payload=response.model_dump(),
        )


def get_image_provider(settings: Settings) -> ImageProvider:
    if settings.image_provider == "openai" and settings.openai_api_key:
        return OpenAIImageProvider(settings)
    return DummyImageProvider(settings)
