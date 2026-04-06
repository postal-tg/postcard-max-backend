"""Add conversation start payload.

Revision ID: 20260406_0002
Revises: 20260406_0001
Create Date: 2026-04-06 20:05:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260406_0002"
down_revision = "20260406_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("conversations", sa.Column("start_payload", sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column("conversations", "start_payload")
