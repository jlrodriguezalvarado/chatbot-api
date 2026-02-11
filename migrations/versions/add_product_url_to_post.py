"""Add product_url to post

Revision ID: add_product_url
Revises: add_vs_record
Create Date: 2026-02-11

"""
from alembic import op
import sqlalchemy as sa


revision = "add_product_url"
down_revision = "add_vs_record"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("post", sa.Column("product_url", sa.String(512), nullable=True))


def downgrade():
    op.drop_column("post", "product_url")
