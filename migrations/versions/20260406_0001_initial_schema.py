"""Initial schema.

Revision ID: 20260406_0001
Revises:
Create Date: 2026-04-06 19:05:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260406_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("max_user_id", sa.BigInteger(), nullable=False),
        sa.Column("username", sa.String(length=255), nullable=True),
        sa.Column("first_name", sa.String(length=255), nullable=True),
        sa.Column("last_name", sa.String(length=255), nullable=True),
        sa.Column("is_bot", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("locale", sa.String(length=32), nullable=True),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("total_requests", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("max_user_id", name="uq_users_max_user_id"),
    )
    op.create_index("ix_users_max_user_id", "users", ["max_user_id"], unique=False)

    op.create_table(
        "conversations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("conversation_type", sa.String(length=32), nullable=False),
        sa.Column("max_chat_id", sa.BigInteger(), nullable=True),
        sa.Column("max_user_id", sa.BigInteger(), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("max_chat_id", name="uq_conversations_max_chat_id"),
        sa.UniqueConstraint("max_user_id", name="uq_conversations_max_user_id"),
    )

    op.create_table(
        "prompts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("conversation_id", sa.Integer(), sa.ForeignKey("conversations.id"), nullable=False),
        sa.Column("source_message_timestamp", sa.BigInteger(), nullable=True),
        sa.Column("raw_text", sa.Text(), nullable=False),
        sa.Column("normalized_text", sa.Text(), nullable=False),
        sa.Column("provider_prompt", sa.Text(), nullable=False),
        sa.Column("prompt_hash", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("validation_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_prompts_user_id", "prompts", ["user_id"], unique=False)
    op.create_index("ix_prompts_conversation_id", "prompts", ["conversation_id"], unique=False)
    op.create_index("ix_prompts_prompt_hash", "prompts", ["prompt_hash"], unique=False)
    op.create_index("ix_prompts_status", "prompts", ["status"], unique=False)

    op.create_table(
        "generation_requests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("prompt_id", sa.Integer(), sa.ForeignKey("prompts.id"), nullable=False),
        sa.Column("provider_name", sa.String(length=64), nullable=False),
        sa.Column("provider_model", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("storage_key", sa.String(length=512), nullable=True),
        sa.Column("public_image_url", sa.String(length=1024), nullable=True),
        sa.Column("max_attachment_token", sa.String(length=512), nullable=True),
        sa.Column("estimated_cost_usd", sa.Float(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("provider_payload", sa.JSON(), nullable=True),
        sa.Column("delivery_payload", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_generation_requests_prompt_id", "generation_requests", ["prompt_id"], unique=False)
    op.create_index("ix_generation_requests_status", "generation_requests", ["status"], unique=False)

    op.create_table(
        "webhook_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("external_id", sa.String(length=255), nullable=False),
        sa.Column("update_type", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("external_id", name="uq_webhook_events_external_id"),
    )
    op.create_index("ix_webhook_events_external_id", "webhook_events", ["external_id"], unique=False)
    op.create_index("ix_webhook_events_update_type", "webhook_events", ["update_type"], unique=False)
    op.create_index("ix_webhook_events_status", "webhook_events", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_webhook_events_status", table_name="webhook_events")
    op.drop_index("ix_webhook_events_update_type", table_name="webhook_events")
    op.drop_index("ix_webhook_events_external_id", table_name="webhook_events")
    op.drop_table("webhook_events")

    op.drop_index("ix_generation_requests_status", table_name="generation_requests")
    op.drop_index("ix_generation_requests_prompt_id", table_name="generation_requests")
    op.drop_table("generation_requests")

    op.drop_index("ix_prompts_status", table_name="prompts")
    op.drop_index("ix_prompts_prompt_hash", table_name="prompts")
    op.drop_index("ix_prompts_conversation_id", table_name="prompts")
    op.drop_index("ix_prompts_user_id", table_name="prompts")
    op.drop_table("prompts")

    op.drop_table("conversations")

    op.drop_index("ix_users_max_user_id", table_name="users")
    op.drop_table("users")
