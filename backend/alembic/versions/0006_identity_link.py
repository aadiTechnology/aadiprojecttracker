"""link users and tenants to Aadi Identity (additive, nullable)

Revision ID: 0006
Revises: 0005
"""
from alembic import op
import sqlalchemy as sa

revision = '0006'
down_revision = '0005'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('users', sa.Column('identity_id', sa.String(36), nullable=True))
    op.create_index('ix_users_identity_id', 'users', ['identity_id'], unique=True)
    op.add_column('tenants', sa.Column('identity_tenant_id', sa.String(36), nullable=True))
    op.create_index('ix_tenants_identity_tenant_id', 'tenants', ['identity_tenant_id'], unique=True)


def downgrade() -> None:
    op.drop_index('ix_tenants_identity_tenant_id', table_name='tenants')
    op.drop_column('tenants', 'identity_tenant_id')
    op.drop_index('ix_users_identity_id', table_name='users')
    op.drop_column('users', 'identity_id')
