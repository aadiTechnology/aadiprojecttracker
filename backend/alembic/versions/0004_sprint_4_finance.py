"""sprint 4 finance and performance

Revision ID: 0004
Revises: 0003
"""
from alembic import op
import sqlalchemy as sa

revision = '0004'
down_revision = '0003'
branch_labels = None
depends_on = None


def _base(*cols):
    return [sa.Column('id', sa.Integer(), nullable=False), sa.Column('tenant_id', sa.Integer(), nullable=False), *cols,
            sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']), sa.PrimaryKeyConstraint('id')]


def upgrade() -> None:
    op.create_table('expenses', *_base(
        sa.Column('category', sa.String(40), nullable=False), sa.Column('vendor', sa.String(120), nullable=False),
        sa.Column('description', sa.String(300), nullable=False), sa.Column('amount_minor', sa.BigInteger(), nullable=False),
        sa.Column('spent_on', sa.Date(), nullable=False), sa.Column('project_id', sa.Integer(), sa.ForeignKey('projects.id'), nullable=True),
        sa.Column('alloc_method', sa.String(12), nullable=False), sa.Column('status', sa.String(10), nullable=False),
        sa.Column('created_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=False), sa.Column('created_at', sa.DateTime(timezone=True), nullable=False)))
    op.create_index('ix_expenses_tenant_id', 'expenses', ['tenant_id'])
    op.create_index('ix_expenses_spent_on', 'expenses', ['spent_on'])
    op.create_index('ix_expenses_project_id', 'expenses', ['project_id'])
    op.create_table('invoices', *_base(
        sa.Column('number', sa.String(30), nullable=False), sa.Column('project_id', sa.Integer(), sa.ForeignKey('projects.id'), nullable=False),
        sa.Column('customer_id', sa.Integer(), sa.ForeignKey('customers.id'), nullable=False), sa.Column('issue_date', sa.Date(), nullable=False),
        sa.Column('due_date', sa.Date(), nullable=False), sa.Column('lines', sa.JSON(), nullable=False), sa.Column('subtotal_minor', sa.BigInteger(), nullable=False),
        sa.Column('tax_pct', sa.Float(), nullable=False), sa.Column('tax_minor', sa.BigInteger(), nullable=False), sa.Column('total_minor', sa.BigInteger(), nullable=False),
        sa.Column('status', sa.String(14), nullable=False), sa.Column('note', sa.String(300), nullable=False),
        sa.Column('created_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=False), sa.Column('approved_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False), sa.UniqueConstraint('tenant_id', 'number')))
    op.create_index('ix_invoices_tenant_id', 'invoices', ['tenant_id'])
    op.create_index('ix_invoices_project_id', 'invoices', ['project_id'])
    op.create_index('ix_invoices_customer_id', 'invoices', ['customer_id'])
    op.create_table('invoice_payments', *_base(
        sa.Column('invoice_id', sa.Integer(), sa.ForeignKey('invoices.id'), nullable=False), sa.Column('amount_minor', sa.BigInteger(), nullable=False),
        sa.Column('paid_on', sa.Date(), nullable=False), sa.Column('reference', sa.String(80), nullable=False),
        sa.Column('recorded_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=False)))
    op.create_index('ix_invoice_payments_tenant_id', 'invoice_payments', ['tenant_id'])
    op.create_index('ix_invoice_payments_invoice_id', 'invoice_payments', ['invoice_id'])
    op.create_table('perf_reviews', *_base(
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False), sa.Column('reviewer_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('month', sa.Date(), nullable=False), sa.Column('dimension', sa.String(30), nullable=False), sa.Column('comment', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False), sa.Column('ack_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('ack_note', sa.String(300), nullable=False)))
    op.create_index('ix_perf_reviews_tenant_id', 'perf_reviews', ['tenant_id'])
    op.create_index('ix_perf_reviews_user_id', 'perf_reviews', ['user_id'])


def downgrade() -> None:
    for t in ('perf_reviews', 'invoice_payments', 'invoices', 'expenses'):
        op.drop_table(t)
