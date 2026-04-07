import hashlib
import re
from dataclasses import dataclass

from postcard_backend.core.config import Settings


@dataclass
class PromptValidationResult:
    is_valid: bool
    raw_text: str
    normalized_text: str
    provider_prompt: str | None = None
    prompt_hash: str | None = None
    error_message: str | None = None


def normalize_user_prompt(raw_text: str, settings: Settings) -> PromptValidationResult:
    plain_text = (raw_text or "").strip()
    plain_text = re.sub(r"\s+", " ", plain_text)

    if not plain_text:
        return PromptValidationResult(
            is_valid=False,
            raw_text=raw_text,
            normalized_text="",
            error_message="Пришлите текстовую тему для открытки.",
        )

    if len(plain_text) > settings.prompt_text_limit:
        return PromptValidationResult(
            is_valid=False,
            raw_text=raw_text,
            normalized_text=plain_text[: settings.prompt_text_limit],
            error_message=(
                f"Тема слишком длинная. В первой версии принимаем сообщения до "
                f"{settings.prompt_text_limit} символов."
            ),
        )

    provider_prompt = (
        f"{settings.postcard_style_preamble}\n"
        f"Theme from user: {plain_text}\n"
        "Create a single postcard image with no visible text, letters, signatures, or captions inside the artwork."
    )
    prompt_hash = hashlib.sha256(plain_text.encode("utf-8")).hexdigest()
    return PromptValidationResult(
        is_valid=True,
        raw_text=raw_text,
        normalized_text=plain_text,
        provider_prompt=provider_prompt,
        prompt_hash=prompt_hash,
    )
