import time
from typing import Any

import httpx
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from postcard_backend.core.config import Settings


def _is_retryable_http_exception(exc: BaseException) -> bool:
    if isinstance(exc, httpx.TransportError):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code >= 500 or exc.response.status_code == 429
    return False


class MaxBotClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.client = httpx.Client(
            base_url=settings.max_api_base_url,
            headers={"Authorization": settings.max_bot_token},
            timeout=30.0,
        )

    @retry(
        retry=retry_if_exception(_is_retryable_http_exception),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    def send_text_message(self, *, user_id: int | None = None, chat_id: int | None = None, text: str) -> dict[str, Any]:
        payload = {"text": text[: self.settings.max_message_text_limit]}
        response = self.client.post("/messages", params=self._target_params(user_id, chat_id), json=payload)
        response.raise_for_status()
        return response.json()

    @retry(
        retry=retry_if_exception(_is_retryable_http_exception),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    def send_image_message(
        self,
        *,
        user_id: int | None = None,
        chat_id: int | None = None,
        text: str,
        attachment_token: str,
        prompt_id: int,
    ) -> dict[str, Any]:
        payload = {
            "text": text[: self.settings.max_message_text_limit],
            "attachments": [
                {
                    "type": "image",
                    "payload": {"token": attachment_token},
                },
                self._build_inline_keyboard(prompt_id),
            ],
        }

        last_error: Exception | None = None
        for attempt in range(1, self.settings.generation_retry_attempts + 1):
            try:
                response = self.client.post("/messages", params=self._target_params(user_id, chat_id), json=payload)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as exc:
                body = exc.response.text
                if "attachment.not.ready" not in body or attempt == self.settings.generation_retry_attempts:
                    raise
                last_error = exc
                time.sleep(self.settings.generation_retry_backoff_seconds * attempt)

        if last_error:
            raise last_error
        raise RuntimeError("Unable to deliver image message to MAX.")

    @retry(
        retry=retry_if_exception(_is_retryable_http_exception),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    def upload_image(self, *, content: bytes, filename: str, content_type: str) -> dict[str, Any]:
        response = self.client.post("/uploads", params={"type": "image"})
        response.raise_for_status()
        upload_data = response.json()
        upload_response = httpx.post(
            upload_data["url"],
            files={"data": (filename, content, content_type)},
            timeout=60.0,
        )
        upload_response.raise_for_status()
        payload = upload_response.json()
        if "token" in payload:
            return payload

        photos = payload.get("photos")
        if isinstance(photos, dict):
            for item in photos.values():
                if isinstance(item, dict) and item.get("token"):
                    return {**payload, "token": item["token"]}

        return payload

    @retry(
        retry=retry_if_exception(_is_retryable_http_exception),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    def answer_callback(self, callback_id: str, notification: str | None = None) -> dict[str, Any]:
        response = self.client.post(
            "/answers",
            params={"callback_id": callback_id},
            json={"notification": notification},
        )
        response.raise_for_status()
        return response.json()

    @retry(
        retry=retry_if_exception(_is_retryable_http_exception),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    def list_subscriptions(self) -> dict[str, Any]:
        response = self.client.get("/subscriptions")
        response.raise_for_status()
        return response.json()

    @retry(
        retry=retry_if_exception(_is_retryable_http_exception),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    def register_subscription(self, *, url: str, update_types: list[str], secret: str) -> dict[str, Any]:
        response = self.client.post(
            "/subscriptions",
            json={"url": url, "update_types": update_types, "secret": secret},
        )
        response.raise_for_status()
        return response.json()

    @retry(
        retry=retry_if_exception(_is_retryable_http_exception),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    def delete_subscription(self, url: str) -> dict[str, Any]:
        response = self.client.request("DELETE", "/subscriptions", params={"url": url})
        response.raise_for_status()
        return response.json()

    @retry(
        retry=retry_if_exception(_is_retryable_http_exception),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    def get_updates(self, *, marker: int | None = None, limit: int = 100, timeout: int = 25) -> dict[str, Any]:
        params: dict[str, Any] = {"limit": limit, "timeout": timeout}
        if marker is not None:
            params["marker"] = marker
        response = self.client.get("/updates", params=params)
        response.raise_for_status()
        return response.json()

    @retry(
        retry=retry_if_exception(_is_retryable_http_exception),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    def get_me(self) -> dict[str, Any]:
        response = self.client.get("/me")
        response.raise_for_status()
        return response.json()

    @staticmethod
    def _target_params(user_id: int | None, chat_id: int | None) -> dict[str, int]:
        if user_id:
            return {"user_id": user_id}
        if chat_id:
            return {"chat_id": chat_id}
        raise ValueError("Either user_id or chat_id must be provided.")

    @staticmethod
    def _build_inline_keyboard(prompt_id: int) -> dict[str, Any]:
        return {
            "type": "inline_keyboard",
            "payload": {
                "buttons": [
                    [
                        {"type": "callback", "text": "Еще вариант", "payload": f"more_variation:{prompt_id}"},
                        {"type": "callback", "text": "Новая тема", "payload": "new_theme"},
                    ]
                ]
            },
        }
