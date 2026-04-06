import csv
import io

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from fastapi.responses import Response

from postcard_backend.core.config import get_settings
from postcard_backend.db.session import get_db
from postcard_backend.models import GenerationRequest, Prompt, User
from postcard_backend.schemas.internal import RecentGeneration, SummaryCard, SummaryResponse
from postcard_backend.services.storage import ObjectStorage

router = APIRouter()
settings = get_settings()


def require_internal_api_key(x_internal_api_key: str = Header(default="")) -> None:
    if x_internal_api_key != settings.internal_api_key:
        raise HTTPException(status_code=401, detail="Invalid internal API key.")


def prompt_to_dict(item: Prompt) -> dict:
    return {
        "id": item.id,
        "user_id": item.user_id,
        "conversation_id": item.conversation_id,
        "status": item.status,
        "raw_text": item.raw_text,
        "normalized_text": item.normalized_text,
        "provider_prompt": item.provider_prompt,
        "prompt_hash": item.prompt_hash,
        "validation_error": item.validation_error,
        "source_message_timestamp": item.source_message_timestamp,
        "created_at": item.created_at.isoformat(),
        "updated_at": item.updated_at.isoformat(),
    }


def generation_to_dict(item: GenerationRequest) -> dict:
    return {
        "id": item.id,
        "prompt_id": item.prompt_id,
        "provider_name": item.provider_name,
        "provider_model": item.provider_model,
        "status": item.status,
        "error_message": item.error_message,
        "public_image_url": item.public_image_url,
        "storage_key": item.storage_key,
        "max_attachment_token": item.max_attachment_token,
        "estimated_cost_usd": item.estimated_cost_usd,
        "latency_ms": item.latency_ms,
        "started_at": item.started_at.isoformat() if item.started_at else None,
        "finished_at": item.finished_at.isoformat() if item.finished_at else None,
        "created_at": item.created_at.isoformat(),
        "updated_at": item.updated_at.isoformat(),
    }


def user_to_dict(item: User) -> dict:
    return {
        "id": item.id,
        "max_user_id": item.max_user_id,
        "username": item.username,
        "first_name": item.first_name,
        "last_name": item.last_name,
        "locale": item.locale,
        "is_bot": item.is_bot,
        "total_requests": item.total_requests,
        "first_seen_at": item.first_seen_at.isoformat(),
        "last_seen_at": item.last_seen_at.isoformat(),
        "created_at": item.created_at.isoformat(),
        "updated_at": item.updated_at.isoformat(),
    }


def csv_response(filename: str, rows: list[dict]) -> Response:
    buffer = io.StringIO()
    if rows:
        writer = csv.DictWriter(buffer, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    content = "\ufeff" + buffer.getvalue()
    return Response(
        content=content,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/summary", response_model=SummaryResponse, dependencies=[Depends(require_internal_api_key)])
def get_summary(db: Session = Depends(get_db)) -> SummaryResponse:
    users = db.scalar(select(func.count()).select_from(User)) or 0
    prompts = db.scalar(select(func.count()).select_from(Prompt)) or 0
    blocked_prompts = db.scalar(select(func.count()).select_from(Prompt).where(Prompt.status == "blocked")) or 0
    generations = db.scalar(select(func.count()).select_from(GenerationRequest)) or 0
    failed_generations = (
        db.scalar(select(func.count()).select_from(GenerationRequest).where(GenerationRequest.status == "failed")) or 0
    )
    active_generations = (
        db.scalar(
            select(func.count())
            .select_from(GenerationRequest)
            .where(GenerationRequest.status.in_(("queued", "processing", "uploading", "sending")))
        )
        or 0
    )

    rows = db.execute(
        select(GenerationRequest, Prompt, User)
        .join(Prompt, Prompt.id == GenerationRequest.prompt_id)
        .join(User, User.id == Prompt.user_id)
        .order_by(GenerationRequest.created_at.desc())
        .limit(10)
    ).all()

    recent = [
        RecentGeneration(
            generation_id=generation.id,
            prompt_id=prompt.id,
            user_id=user.max_user_id,
            username=user.username,
            status=generation.status,
            preview_text=prompt.normalized_text[:120],
            image_url=generation.public_image_url,
            created_at=generation.created_at.isoformat(),
        )
        for generation, prompt, user in rows
    ]

    return SummaryResponse(
        totals=SummaryCard(
            users=users,
            prompts=prompts,
            blocked_prompts=blocked_prompts,
            generations=generations,
            failed_generations=failed_generations,
            active_generations=active_generations,
        ),
        recent_generations=recent,
    )


@router.get("/users", dependencies=[Depends(require_internal_api_key)])
def list_users(
    limit: int = Query(default=20, ge=1, le=200),
    search: str | None = None,
    db: Session = Depends(get_db),
) -> dict:
    query = select(User).order_by(User.last_seen_at.desc()).limit(limit)
    if search:
        pattern = f"%{search}%"
        query = (
            select(User)
            .where((User.username.ilike(pattern)) | (User.first_name.ilike(pattern)) | (User.last_name.ilike(pattern)))
            .order_by(User.last_seen_at.desc())
            .limit(limit)
        )
    users = db.scalars(query).all()
    return {"items": [user_to_dict(item) for item in users]}


@router.get("/users/{user_id}", dependencies=[Depends(require_internal_api_key)])
def get_user_detail(user_id: int, db: Session = Depends(get_db)) -> dict:
    item = db.get(User, user_id)
    if not item:
        raise HTTPException(status_code=404, detail="User not found.")

    prompts = db.scalars(select(Prompt).where(Prompt.user_id == item.id).order_by(Prompt.created_at.desc()).limit(20)).all()
    generations = db.scalars(
        select(GenerationRequest)
        .join(Prompt, Prompt.id == GenerationRequest.prompt_id)
        .where(Prompt.user_id == item.id)
        .order_by(GenerationRequest.created_at.desc())
        .limit(20)
    ).all()

    return {
        "user": user_to_dict(item),
        "recent_prompts": [prompt_to_dict(prompt) for prompt in prompts],
        "recent_generations": [generation_to_dict(generation) for generation in generations],
    }


@router.get("/prompts", dependencies=[Depends(require_internal_api_key)])
def list_prompts(
    limit: int = Query(default=20, ge=1, le=200),
    status: str | None = None,
    db: Session = Depends(get_db),
) -> dict:
    query = select(Prompt).order_by(Prompt.created_at.desc()).limit(limit)
    if status:
        query = select(Prompt).where(Prompt.status == status).order_by(Prompt.created_at.desc()).limit(limit)
    prompts = db.scalars(query).all()
    return {"items": [prompt_to_dict(item) for item in prompts]}


@router.get("/prompts/{prompt_id}", dependencies=[Depends(require_internal_api_key)])
def get_prompt_detail(prompt_id: int, db: Session = Depends(get_db)) -> dict:
    item = db.get(Prompt, prompt_id)
    if not item:
        raise HTTPException(status_code=404, detail="Prompt not found.")

    user = db.get(User, item.user_id)
    generations = db.scalars(
        select(GenerationRequest).where(GenerationRequest.prompt_id == item.id).order_by(GenerationRequest.created_at.desc())
    ).all()
    return {
        "prompt": prompt_to_dict(item),
        "user": user_to_dict(user) if user else None,
        "generations": [generation_to_dict(generation) for generation in generations],
    }


@router.get("/generations", dependencies=[Depends(require_internal_api_key)])
def list_generations(
    limit: int = Query(default=20, ge=1, le=200),
    status: str | None = None,
    db: Session = Depends(get_db),
) -> dict:
    query = select(GenerationRequest).order_by(GenerationRequest.created_at.desc()).limit(limit)
    if status:
        query = (
            select(GenerationRequest)
            .where(GenerationRequest.status == status)
            .order_by(GenerationRequest.created_at.desc())
            .limit(limit)
        )
    items = db.scalars(query).all()
    return {"items": [generation_to_dict(item) for item in items]}


@router.get("/generations/{generation_id}", dependencies=[Depends(require_internal_api_key)])
def get_generation_detail(generation_id: int, db: Session = Depends(get_db)) -> dict:
    item = db.get(GenerationRequest, generation_id)
    if not item:
        raise HTTPException(status_code=404, detail="Generation not found.")

    prompt = db.get(Prompt, item.prompt_id)
    user = db.get(User, prompt.user_id) if prompt else None
    return {
        "generation": generation_to_dict(item),
        "prompt": prompt_to_dict(prompt) if prompt else None,
        "user": user_to_dict(user) if user else None,
    }


@router.get("/generations/{generation_id}/image", dependencies=[Depends(require_internal_api_key)])
def get_generation_image(generation_id: int, db: Session = Depends(get_db)) -> Response:
    item = db.get(GenerationRequest, generation_id)
    if not item:
        raise HTTPException(status_code=404, detail="Generation not found.")
    if not item.storage_key:
        raise HTTPException(status_code=404, detail="Image is not available.")

    content, content_type = ObjectStorage(settings).download_bytes(item.storage_key)
    return Response(content=content, media_type=content_type)


@router.get("/errors", dependencies=[Depends(require_internal_api_key)])
def list_errors(
    limit: int = Query(default=20, ge=1, le=200),
    db: Session = Depends(get_db),
) -> dict:
    items = db.scalars(
        select(GenerationRequest)
        .where(GenerationRequest.status == "failed")
        .order_by(GenerationRequest.updated_at.desc())
        .limit(limit)
    ).all()
    return {"items": [generation_to_dict(item) for item in items]}


@router.get("/exports/users.csv", dependencies=[Depends(require_internal_api_key)])
def export_users(db: Session = Depends(get_db)) -> Response:
    rows = [user_to_dict(item) for item in db.scalars(select(User).order_by(User.id.asc())).all()]
    return csv_response("users.csv", rows)


@router.get("/exports/prompts.csv", dependencies=[Depends(require_internal_api_key)])
def export_prompts(db: Session = Depends(get_db)) -> Response:
    rows = [prompt_to_dict(item) for item in db.scalars(select(Prompt).order_by(Prompt.id.asc())).all()]
    return csv_response("prompts.csv", rows)


@router.get("/exports/generations.csv", dependencies=[Depends(require_internal_api_key)])
def export_generations(db: Session = Depends(get_db)) -> Response:
    rows = [generation_to_dict(item) for item in db.scalars(select(GenerationRequest).order_by(GenerationRequest.id.asc())).all()]
    return csv_response("generations.csv", rows)
