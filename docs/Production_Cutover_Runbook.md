# Production cut-over runbook (Sprint 5)

The deployed site today is a **demo environment** (`APP_ENV=demo`, sample data, shared disposable password). This runbook turns it into a production environment for real customers. Steps marked **Owner** need a decision, a secret or access that only the business owner has. Nothing here has been done for you.

## 1. Decisions and inputs needed (Owner)
| # | Item | Why |
|---|---|---|
| 1 | Production domain names and DNS | Coolify issues TLS; `APP_BASE_URL`, `CRM_UI_URL`, `CRM_API_URL` must point at them |
| 2 | SMTP provider and sender address | Invitations and password resets are emailed (`SMTP_*`) |
| 3 | Backblaze B2 key id, application key, bucket, endpoint | File attachments are not built until these exist (`B2_*`, `STORAGE_PROVIDER`) |
| 4 | Open decisions D-R2-01 to D-R2-15 and the invoice/GST questions in the PRD | The product never assumes a tax rate or revenue basis |
| 5 | Who is the first organization owner (name and email) | Created by invitation, not by seed data |
| 6 | Assistant policy | Default is the rule-based assistant (no model, no cost). A language model needs a vendor, a data-handling decision, and a monthly budget |

## 2. Environment switches
Set in Coolify, never in git:
- `APP_ENV=production` (the app refuses to start without a real `DATABASE_URL` and a `JWT_SECRET` of 32+ random characters)
- `APP_SEED_DEMO=false`, so no sample data is loaded and no shared password exists
- `LOGIN_RATE_PER_MIN=60` (per-address sign-in limit; raise only behind a shared office address)
- `LIVE_SPRINT=5`
- `POSTGRES_PASSWORD`, `JWT_SECRET`: new random values, not the demo ones
- Remove the demo-account list: it is served only when `APP_ENV=demo`

## 3. Database
1. Take a snapshot of the volume before every release.
2. Migrations run on start (`alembic upgrade head`). Keep a **single** app instance until migration is moved to a release step; with several workers starting at once the migration would race.
3. Use a **new** production database. Do not promote the demo database: it contains fictional people and salaries.
4. Schedule nightly `pg_dump` to object storage and test one restore before go-live. Target: RPO 24 h, RTO 4 h (adjust to the business).

## 4. Security checklist (verified in the test suite unless marked)
- [x] Passwords hashed with bcrypt; lockout after repeated failures; per-address rate limit on sign-in and reset
- [x] Tokens expire; "sign out everywhere" exists
- [x] Tenant isolation on every object route (automated sweep in `tests/test_sprint5.py`)
- [x] Server-side money masking; exports and the assistant call the same checks as the screens
- [x] Finance denials (approve, issue) are written to the audit trail
- [x] Security headers: CSP, frame denial, nosniff, referrer policy, permissions policy, HSTS on HTTPS
- [x] CSV exports neutralize spreadsheet formulas
- [ ] Owner: penetration test by a third party before the first paying customer
- [ ] Owner: privacy notice and data-processing terms, because salary data is personal data

## 5. Verification before switching DNS
1. `python -m pytest backend/tests` (all green).
2. `node videos/check-screens.mjs` against the production URL with a test organization.
3. `node videos/check-a11y.mjs`: no serious or critical findings.
4. `python backend/loadtest.py <url> 30 20` on staging: no errors, p95 under 2 s. Measured on a developer laptop with one worker: about 55 requests per second, p95 0.73 s at 30 concurrent users.
5. Sign in as each role and open the menu: items the role cannot use are hidden.

## 6. Cut-over day
1. Announce a short freeze. Snapshot the staging database.
2. Deploy with the production environment. Confirm `/api/health` shows `"env":"production"`.
3. Create the first organization through the platform administration screen and invite its owner by email.
4. Owner signs in, sets costing defaults, departments, tags and entitlements (the AI assistant module is **off** until switched on per organization).
5. Smoke test: invite, reset password, create customer, project, allocation, timesheet, invoice draft.
6. Watch logs and the audit trail for the first day.

## 7. Rollback
Redeploy the previous image in Coolify and restore the pre-release snapshot. Migrations 0001 to 0005 have `downgrade` steps for the newest tables only; restoring the snapshot is the supported path.

## 8. Not included in this release
Backblaze attachments, XLSX and PDF export (CSV only), a language-model assistant, multi-worker deployment, mobile screens for costing, insights, finance and the assistant.
