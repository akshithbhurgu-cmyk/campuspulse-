"""add an optional display title to timetable entries

Revision ID: c7a1d8e4f603
Revises: 8e4c5f1a9d22
"""

from alembic import op
import sqlalchemy as sa

revision = "c7a1d8e4f603"
down_revision = "8e4c5f1a9d22"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("timetable_entries", sa.Column("title", sa.String(length=180), nullable=True))


def downgrade() -> None:
    op.drop_column("timetable_entries", "title")
