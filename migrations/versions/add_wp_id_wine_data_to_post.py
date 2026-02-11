"""Add wp_id and wine_data to post

Revision ID: add_wp_wine
Revises: 6a379803e1c4
Create Date: 2026-02-11

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_wp_wine'
down_revision = '6a379803e1c4'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('post', sa.Column('wp_id', sa.Integer(), nullable=True))
    op.add_column('post', sa.Column('wine_data', sa.JSON(), nullable=True))
    op.create_index(op.f('ix_post_wp_id'), 'post', ['wp_id'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_post_wp_id'), table_name='post')
    op.drop_column('post', 'wine_data')
    op.drop_column('post', 'wp_id')
