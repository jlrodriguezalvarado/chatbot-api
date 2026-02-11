"""Add vector_store_record table

Revision ID: add_vs_record
Revises: add_wp_wine
Create Date: 2026-02-11

"""
from alembic import op
import sqlalchemy as sa


revision = "add_vs_record"
down_revision = "add_wp_wine"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "vector_store_record",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("vector_store_id", sa.String(128), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_vector_store_record_vector_store_id"), "vector_store_record", ["vector_store_id"], unique=False)


def downgrade():
    op.drop_index(op.f("ix_vector_store_record_vector_store_id"), table_name="vector_store_record")
    op.drop_table("vector_store_record")
