"""retire Project Tracker's own copies of people, roles and departments (the shared organisation kit is now the only copy)

Revision ID: 0009
Revises: 0008

What this does, in order, inside one transaction:
  1. snapshot: copies roles, departments and memberships into retired_roles, retired_departments and retired_memberships (kept in the
     database, so nothing is lost even if no external backup was taken; drop them later with DROP TABLE once you are satisfied);
  2. bring the shared tables up to date with the old ones one last time (the old tables were always at least as fresh as the shared ones);
  3. drop role_id, title, manager_user_id, department_id, status and kit_id from memberships, then drop roles and departments.

memberships keeps only team and hours_override: what the shared kit does not know about a person. Downgrade restores the dropped columns and
tables from the snapshots.
"""
from datetime import datetime, timezone

import sqlalchemy as sa
from alembic import op

revision = '0009'
down_revision = '0008'
branch_labels = None
depends_on = None


def _to_kit(perms):
    out = [("audit.view" if p.startswith("audit.view:") else p) for p in perms if p != "org.admin"]
    if "org.admin" in perms or "departments.manage" in perms:
        out.append("org.departments.manage")
    if "org.admin" in perms:
        out += ["org.users.view", "org.users.manage", "org.roles.manage"]
    return sorted(set(out))


def _tables(bind, names):
    md = sa.MetaData()
    return {n: sa.Table(n, md, autoload_with=bind) for n in names}


def _bring_shared_tables_up_to_date(bind):
    t = _tables(bind, ("users", "roles", "departments", "memberships", "org_roles", "org_departments", "org_members"))
    users, roles, depts, mems = t["users"], t["roles"], t["departments"], t["memberships"]
    kroles, kdepts, kmems = t["org_roles"], t["org_departments"], t["org_members"]

    def insert(table, values):
        return bind.execute(sa.insert(table).values(**values)).inserted_primary_key[0]

    role_kit = {}
    for r in bind.execute(sa.select(roles)).mappings().all():
        tk = str(r["tenant_id"])
        kid = r["kit_id"]
        row = bind.execute(sa.select(kroles).where(kroles.c.id == kid)).mappings().first() if kid else None
        if row is None:
            row = bind.execute(sa.select(kroles).where(kroles.c.tenant_id == tk, kroles.c.key == r["key"])).mappings().first()
        vals = dict(key=r["key"], name=r["name"], caps=_to_kit(list(r["perms"] or [])), is_system=bool(r["is_system"]))
        if row is None:
            kid = insert(kroles, dict(tenant_id=tk, description="", **vals))
        else:
            kid = row["id"]
            bind.execute(sa.update(kroles).where(kroles.c.id == kid).values(**vals))
        role_kit[r["id"]] = kid

    dept_kit = {}
    for d in bind.execute(sa.select(depts)).mappings().all():
        tk = str(d["tenant_id"])
        kid = d["kit_id"]
        row = bind.execute(sa.select(kdepts).where(kdepts.c.id == kid)).mappings().first() if kid else None
        if row is None:
            row = bind.execute(sa.select(kdepts).where(kdepts.c.tenant_id == tk, kdepts.c.name == d["name"])).mappings().first()
        if row is None:
            kid = insert(kdepts, dict(tenant_id=tk, name=d["name"]))
        else:
            kid = row["id"]
            bind.execute(sa.update(kdepts).where(kdepts.c.id == kid).values(name=d["name"]))
        dept_kit[d["id"]] = kid

    member_kit = {}  # Tracker user id -> kit member id, per tenant
    rows = bind.execute(sa.select(mems, users.c.email, users.c.name.label("uname"), users.c.status.label("ustatus"), users.c.identity_id).join(users, users.c.id == mems.c.user_id)).mappings().all()
    for r in rows:
        tk = str(r["tenant_id"])
        email = r["email"].lower()
        kid = r["kit_id"]
        row = bind.execute(sa.select(kmems).where(kmems.c.id == kid)).mappings().first() if kid else None
        if row is None:
            row = bind.execute(sa.select(kmems).where(kmems.c.tenant_id == tk, kmems.c.email == email)).mappings().first()
        status = "suspended" if (r["status"] == "suspended" or r["ustatus"] == "suspended") else ("invited" if r["ustatus"] == "invited" else "active")
        vals = dict(user_id=str(r["user_id"]), identity_id=r["identity_id"], email=email, name=r["uname"], title=r["title"] or "",
                    role_id=role_kit[r["role_id"]], department_id=dept_kit.get(r["department_id"]), status=status)
        if row is None:
            kid = insert(kmems, dict(tenant_id=tk, created_at=datetime.now(timezone.utc), **vals))  # reflected tables have no Python-side defaults
        else:
            kid = row["id"]
            bind.execute(sa.update(kmems).where(kmems.c.id == kid).values(**vals))
        member_kit[(r["tenant_id"], r["user_id"])] = kid
    for r in rows:  # reporting lines, once everyone has a kit id
        mgr = member_kit.get((r["tenant_id"], r["manager_user_id"])) if r["manager_user_id"] else None
        bind.execute(sa.update(kmems).where(kmems.c.id == member_kit[(r["tenant_id"], r["user_id"])]).values(manager_id=mgr))
    for d in bind.execute(sa.select(depts)).mappings().all():
        head = member_kit.get((d["tenant_id"], d["head_user_id"])) if d["head_user_id"] else None
        bind.execute(sa.update(kdepts).where(kdepts.c.id == dept_kit[d["id"]]).values(head_member_id=head))


def upgrade() -> None:
    bind = op.get_bind()
    for table in ("roles", "departments", "memberships"):
        bind.exec_driver_sql(f"DROP TABLE IF EXISTS retired_{table}")  # left behind by an earlier upgrade that was then undone
        bind.exec_driver_sql(f"CREATE TABLE retired_{table} AS SELECT * FROM {table}")
    _bring_shared_tables_up_to_date(bind)
    for col in ("role_id", "title", "manager_user_id", "department_id", "status"):
        op.drop_column("memberships", col)
    op.drop_index("ix_memberships_kit_id", table_name="memberships")
    op.drop_column("memberships", "kit_id")
    op.drop_table("departments")
    op.drop_table("roles")


def downgrade() -> None:
    bind = op.get_bind()
    op.create_table("roles", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=False, index=True),
                    sa.Column("key", sa.String(40), nullable=False), sa.Column("name", sa.String(120), nullable=False), sa.Column("perms", sa.JSON(), nullable=False),
                    sa.Column("is_system", sa.Boolean(), nullable=False), sa.Column("kit_id", sa.Integer(), nullable=True), sa.UniqueConstraint("tenant_id", "key"))
    op.create_table("departments", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=False, index=True),
                    sa.Column("name", sa.String(80), nullable=False), sa.Column("head_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
                    sa.Column("kit_id", sa.Integer(), nullable=True), sa.UniqueConstraint("tenant_id", "name"))
    for table, cols in (("roles", "id, tenant_id, key, name, perms, is_system, kit_id"), ("departments", "id, tenant_id, name, head_user_id, kit_id")):
        bind.exec_driver_sql(f"INSERT INTO {table} ({cols}) SELECT {cols} FROM retired_{table}")
    op.add_column("memberships", sa.Column("role_id", sa.Integer(), sa.ForeignKey("roles.id"), nullable=True))
    op.add_column("memberships", sa.Column("title", sa.String(120), nullable=False, server_default=""))
    op.add_column("memberships", sa.Column("manager_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True))
    op.add_column("memberships", sa.Column("department_id", sa.Integer(), sa.ForeignKey("departments.id"), nullable=True))
    op.add_column("memberships", sa.Column("status", sa.String(20), nullable=False, server_default="active"))
    op.add_column("memberships", sa.Column("kit_id", sa.Integer(), nullable=True))
    op.create_index("ix_memberships_kit_id", "memberships", ["kit_id"])
    bind.exec_driver_sql("UPDATE memberships SET role_id = r.role_id, title = r.title, manager_user_id = r.manager_user_id, department_id = r.department_id, "
                         "status = r.status, kit_id = r.kit_id FROM retired_memberships r WHERE r.id = memberships.id")
    op.alter_column("memberships", "role_id", nullable=False)
