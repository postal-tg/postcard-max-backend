import logging
from datetime import datetime, timezone

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from postcard_backend.core.config import get_settings
from postcard_backend.db.session import new_session
from postcard_backend.models import Conversation, GenerationRequest, Prompt, User, WebhookEvent
from postcard_backend.schemas.max_models import MaxUpdateSchema
from postcard_backend.services.image_provider import get_image_provider
from postcard_backend.services.max_client import MaxBotClient
from postcard_backend.services.message_templates import (
    active_generation_message,
    blocked_prompt_message,
    callback_missing_prompt_message,
    callback_more_variation_message,
    callback_new_theme_message,
    callback_unknown_message,
    generation_failed_message,
    generation_ready_message,
    generation_started_message,
    help_message,
    invalid_prompt_message,
    rate_limit_message,
    welcome_message,
)
from postcard_backend.services.moderation import moderate_prompt
from postcard_backend.services.prompt_builder import normalize_user_prompt
from postcard_backend.services.rate_limiter import RedisRateLimiter
from postcard_backend.services.storage import ObjectStorage
from postcard_backend.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)
settings = get_settings()


@celery_app.task(name="postcard_backend.process_webhook_event")
def process_webhook_event(event_id: int) -> None:
    with new_session() as db:
        event = db.get(WebhookEvent, event_id)
        if not event:
            return

        try:
            event.status = "processing"
            db.commit()
            update = MaxUpdateSchema.model_validate(event.payload)

            if update.update_type == "message_created":
                _handle_message_created(db, update)
            elif update.update_type == "message_callback":
                _handle_callback(db, update)
            elif update.update_type == "bot_started":
                _handle_bot_started(db, update)
            else:
                event.status = "ignored"

            event.processed_at = datetime.now(timezone.utc)
            if event.status == "processing":
                event.status = "processed"
            db.commit()
        except Exception as exc:
            logger.exception("Webhook event failed", extra={"event_id": event_id})
            event.status = "failed"
            event.error_message = str(exc)
            event.processed_at = datetime.now(timezone.utc)
            db.commit()


def _handle_message_created(db: Session, update: MaxUpdateSchema) -> None:
    message = update.message
    if not message or not message.sender:
        return

    raw_text = message.body.text if message.body and message.body.text else ""
    user = _upsert_user(db, update)
    conversation = _upsert_conversation(db, chat_id=message.recipient.chat_id, max_user_id=user.max_user_id, title=user.first_name)
    max_client = MaxBotClient(settings)

    command = raw_text.strip().lower()
    if command == "/start":
        max_client.send_text_message(user_id=user.max_user_id, text=welcome_message(settings.max_bot_name))
        return
    if command == "/help":
        max_client.send_text_message(user_id=user.max_user_id, text=help_message(settings.max_bot_name))
        return

    rate_limit = RedisRateLimiter(settings).check(RedisRateLimiter.user_key(user.max_user_id, action="incoming_message"))
    if not rate_limit.is_allowed:
        max_client.send_text_message(user_id=user.max_user_id, text=rate_limit_message(rate_limit.retry_after_seconds))
        return

    validation = normalize_user_prompt(raw_text, settings)
    if not validation.is_valid:
        max_client.send_text_message(
            user_id=user.max_user_id,
            text=validation.error_message or invalid_prompt_message(),
        )
        return

    moderation = moderate_prompt(validation.normalized_text, settings)
    if not moderation.is_allowed:
        blocked_prompt = Prompt(
            user_id=user.id,
            conversation_id=conversation.id,
            source_message_timestamp=message.timestamp,
            raw_text=validation.raw_text,
            normalized_text=validation.normalized_text,
            provider_prompt="",
            prompt_hash=validation.prompt_hash or "",
            status="blocked",
            validation_error=moderation.error_message,
        )
        db.add(blocked_prompt)
        db.commit()
        max_client.send_text_message(user_id=user.max_user_id, text=blocked_prompt_message())
        return

    active_generations = _count_active_generations(db, user.id)
    if active_generations and active_generations >= settings.max_active_generations_per_user:
        max_client.send_text_message(user_id=user.max_user_id, text=active_generation_message())
        return

    prompt = Prompt(
        user_id=user.id,
        conversation_id=conversation.id,
        source_message_timestamp=message.timestamp,
        raw_text=validation.raw_text,
        normalized_text=validation.normalized_text,
        provider_prompt=validation.provider_prompt or "",
        prompt_hash=validation.prompt_hash or "",
        status="accepted",
    )
    db.add(prompt)
    user.total_requests += 1
    db.commit()
    db.refresh(prompt)

    generation = GenerationRequest(
        prompt_id=prompt.id,
        provider_name=settings.image_provider,
        provider_model=settings.openai_image_model if settings.image_provider == "openai" else "local-preview",
        status="queued",
    )
    db.add(generation)
    db.commit()
    db.refresh(generation)

    max_client.send_text_message(user_id=user.max_user_id, text=generation_started_message(validation.normalized_text))
    generate_postcard.delay(generation.id)


def _handle_callback(db: Session, update: MaxUpdateSchema) -> None:
    callback = update.callback
    if not callback:
        return

    max_client = MaxBotClient(settings)
    payload = callback.payload or ""

    if payload.startswith("more_variation:"):
        try:
            prompt_id = int(payload.split(":", maxsplit=1)[1])
        except (IndexError, ValueError):
            max_client.answer_callback(callback.callback_id, notification=callback_unknown_message())
            return

        prompt = db.get(Prompt, prompt_id)
        if not prompt:
            max_client.answer_callback(callback.callback_id, notification=callback_missing_prompt_message())
            return

        rate_limit = RedisRateLimiter(settings).check(
            RedisRateLimiter.user_key(prompt.user.max_user_id, action="callback_more_variation")
        )
        if not rate_limit.is_allowed:
            max_client.answer_callback(
                callback.callback_id,
                notification=rate_limit_message(rate_limit.retry_after_seconds),
            )
            return

        active_generations = _count_active_generations(db, prompt.user_id)
        if active_generations and active_generations >= settings.max_active_generations_per_user:
            max_client.answer_callback(callback.callback_id, notification=active_generation_message())
            return

        generation = GenerationRequest(
            prompt_id=prompt.id,
            provider_name=settings.image_provider,
            provider_model=settings.openai_image_model if settings.image_provider == "openai" else "local-preview",
            status="queued",
        )
        db.add(generation)
        db.commit()
        db.refresh(generation)

        max_client.answer_callback(callback.callback_id, notification=callback_more_variation_message())
        generate_postcard.delay(generation.id)
        return

    if payload == "new_theme":
        max_client.answer_callback(callback.callback_id, notification=callback_new_theme_message())
        return

    max_client.answer_callback(callback.callback_id, notification=callback_unknown_message())


def _handle_bot_started(db: Session, update: MaxUpdateSchema) -> None:
    if not update.user or not update.chat_id:
        return

    user = _upsert_user_from_started_payload(db, update)
    _upsert_conversation(
        db,
        chat_id=update.chat_id,
        max_user_id=user.max_user_id,
        title=user.first_name,
        start_payload=update.payload,
    )
    MaxBotClient(settings).send_text_message(user_id=user.max_user_id, text=welcome_message(settings.max_bot_name))


@celery_app.task(name="postcard_backend.generate_postcard")
def generate_postcard(generation_id: int) -> None:
    with new_session() as db:
        generation = db.get(GenerationRequest, generation_id)
        if not generation:
            return

        prompt = generation.prompt
        user = prompt.user
        generation.status = "processing"
        generation.started_at = datetime.now(timezone.utc)
        db.commit()

        try:
            provider = get_image_provider(settings)
            storage = ObjectStorage(settings)
            max_client = MaxBotClient(settings)

            generated = provider.generate(prompt.provider_prompt)
            generation.provider_name = generated.provider_name
            generation.provider_model = generated.model
            generation.estimated_cost_usd = generated.estimated_cost_usd
            generation.provider_payload = generated.payload
            generation.status = "uploading"
            db.commit()

            storage_key, public_url = storage.upload_bytes(generated.content, generated.content_type)
            generation.storage_key = storage_key
            generation.public_image_url = public_url
            db.commit()

            upload_payload = max_client.upload_image(
                content=generated.content,
                filename=f"postcard-{generation.id}.png",
                content_type=generated.content_type,
            )
            token = upload_payload["token"]

            generation.max_attachment_token = token
            generation.status = "sending"
            db.commit()

            delivery_payload = max_client.send_image_message(
                user_id=user.max_user_id,
                text=generation_ready_message(prompt.normalized_text),
                attachment_token=token,
                prompt_id=prompt.id,
            )
            generation.delivery_payload = delivery_payload
            generation.status = "completed"
            generation.finished_at = datetime.now(timezone.utc)

            if generation.started_at:
                delta = generation.finished_at - generation.started_at
                generation.latency_ms = int(delta.total_seconds() * 1000)
            db.commit()
        except Exception as exc:
            logger.exception("Generation failed", extra={"generation_id": generation_id})
            generation.status = "failed"
            generation.error_message = str(exc)
            generation.finished_at = datetime.now(timezone.utc)
            db.commit()

            try:
                MaxBotClient(settings).send_text_message(
                    user_id=user.max_user_id,
                    text=generation_failed_message(),
                )
            except Exception:
                logger.exception("Unable to notify user about generation failure", extra={"generation_id": generation_id})


def _count_active_generations(db: Session, user_id: int) -> int:
    return db.scalar(
        select(func.count())
        .select_from(GenerationRequest)
        .join(Prompt, Prompt.id == GenerationRequest.prompt_id)
        .where(
            and_(
                Prompt.user_id == user_id,
                GenerationRequest.status.in_(("queued", "processing", "uploading", "sending")),
            )
        )
    ) or 0


def _upsert_user(db: Session, update: MaxUpdateSchema) -> User:
    message = update.message
    if not message or not message.sender:
        raise ValueError("Message sender is required to upsert a user.")

    sender = message.sender
    return _persist_user(
        db,
        max_user_id=sender.user_id,
        username=sender.username,
        first_name=sender.first_name,
        last_name=sender.last_name,
        is_bot=bool(sender.is_bot),
        locale=update.user_locale,
    )


def _upsert_user_from_started_payload(db: Session, update: MaxUpdateSchema) -> User:
    if not update.user:
        raise ValueError("Started payload user is required to upsert a user.")
    sender = update.user
    return _persist_user(
        db,
        max_user_id=sender.user_id,
        username=sender.username,
        first_name=sender.first_name,
        last_name=sender.last_name,
        is_bot=bool(sender.is_bot),
        locale=update.user_locale,
    )


def _persist_user(
    db: Session,
    *,
    max_user_id: int,
    username: str | None,
    first_name: str | None,
    last_name: str | None,
    is_bot: bool,
    locale: str | None,
) -> User:
    user = db.scalar(select(User).where(User.max_user_id == max_user_id))
    now = datetime.now(timezone.utc)
    if user is None:
        user = User(
            max_user_id=max_user_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
            is_bot=is_bot,
            locale=locale,
            first_seen_at=now,
            last_seen_at=now,
        )
        db.add(user)
    else:
        user.username = username
        user.first_name = first_name
        user.last_name = last_name
        user.locale = locale
        user.last_seen_at = now
    db.commit()
    db.refresh(user)
    return user


def _upsert_conversation(
    db: Session,
    *,
    chat_id: int | None,
    max_user_id: int | None,
    title: str | None,
    start_payload: str | None = None,
) -> Conversation:
    conversation = db.scalar(select(Conversation).where(Conversation.max_user_id == max_user_id))
    if conversation is None:
        conversation = Conversation(
            conversation_type="direct",
            max_chat_id=chat_id,
            max_user_id=max_user_id,
            title=title,
            start_payload=start_payload,
        )
        db.add(conversation)
        db.commit()
        db.refresh(conversation)
    else:
        conversation.max_chat_id = chat_id or conversation.max_chat_id
        conversation.title = title or conversation.title
        if start_payload:
            conversation.start_payload = start_payload
        db.commit()
        db.refresh(conversation)
    return conversation
