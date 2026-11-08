"""identity events already applied (idempotent delivery)

Revision ID: 0007
Revises: 0006
"""
from alembic import op
import sqlalchemy as sa

revision = '0007'
down_revision = '0006'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('identity_events',
                    sa.Column('id', sa.String(36), nullable=False), sa.Column('type', sa.String(40), nullable=False),
                    sa.Column('received_at', sa.DateTime(timezone=True), nullable=False), sa.PrimaryKeyConstraint('id'))


def downgrade() -> None:
    op.drop_table('identity_events')
