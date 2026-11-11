# People, roles and departments in Project Tracker (K3 and the clean-up)

## Where things live

| What | Where |
|---|---|
| Who is in a company, their role, title, department, manager, status | the shared organisation kit: `org_members` |
| Roles and what each may do | `org_roles` (capabilities, stored per company) |
| Departments and their heads | `org_departments` |
| A person's team and monthly-hours override | Tracker's `memberships` table (profile): the two things the kit does not know |
| Sign-in accounts | `users` (unchanged) |

Everything in Tracker asks `app/people.py`; `app/org_kit.py` holds the Tracker-specific parts of the kit (capabilities catalogue, the translation of `org.admin`, the salary rule, Identity hooks). Before this release Tracker kept its own copies in `roles`, `departments` and in columns of `memberships`, kept equal to the kit by two copy passes. They are gone.

## Statuses

A person is `active`, `invited` (the account has no password yet) or `suspended`. "Live" (active or invited) are the people a company has and can give work to; only `active` people sign in. Setting a password changes `invited` to `active` everywhere. Suspending a person refuses them on their next request, because the company membership is checked on every request.

## IDs changed

Role and department ids are now the kit's ids, so they differ from the old ones. Tracker's screens read them from the API every time, so nothing is typed in by hand; anything you saved outside the app that stores a department or role id (a bookmarked URL, a script) needs the new id.

## The migration (0009)

Runs once, in one transaction, on the next start:

1. copies `roles`, `departments` and `memberships` into **`retired_roles`, `retired_departments`, `retired_memberships`** (a snapshot inside the database);
2. brings the shared tables up to date from the old ones one last time (the old tables were always at least as fresh);
3. drops the old columns of `memberships`, and the `roles` and `departments` tables.

It was rehearsed on a PostgreSQL database shaped like production before the change, with stale and missing shared rows: the stale rows were corrected, the missing person added, reporting lines, department heads, statuses and hours kept, and the downgrade restored the old tables and columns from the snapshots.

**After the release has run a while and you are satisfied**, remove the snapshots: `DROP TABLE retired_roles, retired_departments, retired_memberships;`

## Rolling back

`alembic downgrade 0008` restores the dropped tables and columns from the snapshots. It needs the `retired_*` tables, so do not drop them until you will not roll back. Roll back the application image together with the database.
