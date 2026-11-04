# Aadi Project Tracker

Business Performance & Project Profitability platform (PRD in [docs/](docs/)). Multi-tenant SaaS with role-based access, one web app and (from Sprint 2) one mobile app.

| Layer | Technology |
|---|---|
| Web | React 19, TypeScript, Vite (responsive) |
| API | Python FastAPI, SQLAlchemy 2, Alembic |
| Database | PostgreSQL 16 |
| Mobile | Expo / React Native (Sprint 2 onward) |
| Email | SMTP (Brevo relay) |
| Files | S3-compatible object storage, Backblaze B2 (Sprint 3) |

## Sprints (4)
| Sprint | Backend + web (+ mobile from S2) | Demo video |
|---|---|---|
| **S1 Foundation** (done) | Sign-in, invitations/reset by email, tenants, roles as data, entitlements, audit, customers, projects, scope changes, role-aware dashboard, demo accounts | `videos/01-sprint-1-foundation-and-projects.mp4` |
| S2 Delivery | Sprints, tasks, handover, timesheets and approval; mobile app (my tasks, timesheet, handover) | planned |
| S3 Money | Revenue targets, expenses and allocation, invoices, performance matrix, attachments on Backblaze | planned |
| S4 Hardening | AI assistant (advisory), reports/exports, accessibility, load and security pass, production cut-over | planned |

## Run locally
```
docker compose up -d                                   # PostgreSQL on localhost:15434
cd backend && python -m venv .venv && .venv/Scripts/pip install -r requirements.txt
set APP_ENV=demo && python -m app.seed --reset         # demo data (demo mode only)
python -m uvicorn app.main:app --port 8000             # serves the API and the built web app
cd ../frontend && npm install && npm run build         # or npm run dev (port 5173, proxies /api)
```
Demo sign-ins are listed under the Sign in button (shared disposable password, demo environment only). All data is fictional.

## Tests
```
cd backend && python -m pytest tests -q               # needs the tracker_test database
cd videos && node check-screens.mjs                   # every persona signs in and opens every screen
```

## Deploy (Coolify)
`python deploy/coolify_deploy.py` reads `.env.coolify` (git-ignored, see `.env.coolify.example`) and creates/updates the Coolify resource from `docker-compose.coolify.yml`. Web `https://aadiprojecttracker.aaditechnology.com`, API `https://aadiprojecttrackerapi.aaditechnology.com`.

## Governance
Proposed defaults are not customer approvals. Revenue basis and the meaning of the S/H planning markers are stored as *undecided* until the customer decides.
