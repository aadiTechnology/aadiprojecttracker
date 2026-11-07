"""sprint 5 advisory assistant usage log

Revision ID: 0005
Revises: 0004
"""
from alembic import op
import sqlalchemy as sa

revision = '0005'
down_revision = '0004'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('ai_usage_log',
                    sa.Column('id', sa.Integer(), nullable=False), sa.Column('tenant_id', sa.Integer(), nullable=False),
                    sa.Column('user_id', sa.Integer(), nullable=False), sa.Column('question', sa.String(300), nullable=False),
                    sa.Column('intent', sa.String(30), nullable=False), sa.Column('provider', sa.String(20), nullable=False),
                    sa.Column('tokens_in', sa.Integer(), nullable=False), sa.Column('tokens_out', sa.Integer(), nullable=False),
                    sa.Column('cost_minor', sa.BigInteger(), nullable=False), sa.Column('at', sa.DateTime(timezone=True), nullable=False),
                    sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']), sa.ForeignKeyConstraint(['user_id'], ['users.id']), sa.PrimaryKeyConstraint('id'))
    op.create_index('ix_ai_usage_log_tenant_id', 'ai_usage_log', ['tenant_id'])
    op.create_index('ix_ai_usage_log_user_id', 'ai_usage_log', ['user_id'])
    op.create_index('ix_ai_usage_log_at', 'ai_usage_log', ['at'])


def downgrade() -> None:
    op.drop_table('ai_usage_log')
