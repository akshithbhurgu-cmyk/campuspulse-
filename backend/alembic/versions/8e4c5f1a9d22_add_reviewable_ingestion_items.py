"""add reviewable ingestion items

Revision ID: 8e4c5f1a9d22
Revises: 2191729eb9e3
"""
from alembic import op
import sqlalchemy as sa

revision = "8e4c5f1a9d22"
down_revision = "2191729eb9e3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ingestion_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("course_id", sa.Integer(), nullable=True),
        sa.Column("source", sa.String(length=16), nullable=False),
        sa.Column("external_id", sa.String(length=255), nullable=True),
        sa.Column("filename", sa.String(length=255), nullable=True),
        sa.Column("raw_text", sa.Text(), nullable=False),
        sa.Column("normalized_text", sa.Text(), nullable=False),
        sa.Column("extraction", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("source IN ('PASTE', 'PDF', 'GMAIL')", name="ck_ingestion_source"),
        sa.CheckConstraint("status IN ('PREVIEW', 'APPLIED', 'IGNORED', 'FAILED')", name="ck_ingestion_status"),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("external_id"),
    )
    op.create_index(op.f("ix_ingestion_items_student_id"), "ingestion_items", ["student_id"])
    op.create_index(op.f("ix_ingestion_items_course_id"), "ingestion_items", ["course_id"])
    op.create_index(op.f("ix_ingestion_items_status"), "ingestion_items", ["status"])


def downgrade() -> None:
    op.drop_index(op.f("ix_ingestion_items_status"), table_name="ingestion_items")
    op.drop_index(op.f("ix_ingestion_items_course_id"), table_name="ingestion_items")
    op.drop_index(op.f("ix_ingestion_items_student_id"), table_name="ingestion_items")
    op.drop_table("ingestion_items")
