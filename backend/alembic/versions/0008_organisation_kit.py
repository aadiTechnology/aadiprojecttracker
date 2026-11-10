"""shared organisation kit tables, and the link from Tracker's own rows to them

Revision ID: 0008
Revises: 0007

Adds org_departments, org_roles, org_members, org_audit and a nullable kit_id on roles, memberships and departments.
Existing people are copied into the kit the first time each company is opened (and at start-up), by app.org_kit.pull,
so this revision only changes the schema.
"""
import sqlalchemy as sa
from alembic import op

revision = '0008'
down_revision = '0007'
branch_labels = None
depends_on = None


def upgrade() -> None:
    from aadi_org import migration
    from app.models import KIT
    insp = sa.inspect(op.get_bind())
    for table in ("roles", "memberships", "departments"):
        if "kit_id" not in {c["name"] for c in insp.get_columns(table)}:
            op.add_column(table, sa.Column("kit_id", sa.Integer(), nullable=True))
            op.create_index(f"ix_{table}_kit_id", table, ["kit_id"])
    migration.create_tables(op.get_bind(), KIT)


def downgrade() -> None:
    from aadi_org import migration
    from app.models import KIT
    migration.drop_tables(op.get_bind(), KIT)
    for table in ("roles", "memberships", "departments"):
        op.drop_index(f"ix_{table}_kit_id", table_name=table)
        op.drop_column(table, "kit_id")
