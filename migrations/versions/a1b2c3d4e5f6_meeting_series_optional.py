"""make meeting.series_id nullable (one-off meetings)

Revision ID: a1b2c3d4e5f6
Revises: b64c66cbe2d5
Create Date: 2026-09-04 11:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'a1b2c3d4e5f6'
down_revision = 'b64c66cbe2d5'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('meeting') as batch:
        batch.alter_column('series_id', existing_type=sa.Integer(), nullable=True)


def downgrade():
    with op.batch_alter_table('meeting') as batch:
        batch.alter_column('series_id', existing_type=sa.Integer(), nullable=False)
