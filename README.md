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

## Sprints (5)
| Sprint | Backend + web (+ mobile from S2) | Demo video |
|---|---|---|
| **S1 Foundation** (done) | Sign-in, invitations/reset by email, tenants, roles as data, entitlements, audit, customers, projects, scope changes, role-aware dashboard, demo accounts | `videos/01-sprint-1-foundation-and-projects.mp4` |
| **S2 Delivery** (done) | Sprints, tasks with assignment history, handover + acknowledgement, timesheets + approval, notification bell, role dashboards (web); Expo mobile app (my tasks, timesheet, handover, alerts) | `videos/02-sprint-2-delivery-web.mp4`, `videos/02-sprint-2-mobile-app.mp4` |
| **S3 Costing & Profitability** (done) | PRD Revision 2: employees, departments and salary (restricted), project tags, monthly allocation (max 100%), costing settings (160 h, ₹250), effort and cost by employee/project/tag and workbook-style matrix, revenue targets, project profitability, tag analysis. 72 backend tests. Also a second demo organization shaped like the Matrix workbook and the Decision Insights views (CEO, Product Owner, Project Manager) | `videos/04-sprint-3-costing-and-profitability.mp4`, `videos/05-decision-insights-matrix-organization.mp4` |
| **S4 Finance & performance** (done, except attachments) | Expenses (direct and shared, with equal / hours / headcount split that always reconciles), invoices (draft, CEO approval, issue, payments, derived overdue, audited denials), planned vs actual from approved timesheets, project contribution (value, salary, direct, shared; invoiced and collected kept apart), performance matrix with evidence-based review comments and employee acknowledgement (no score, no ranking). Backblaze file attachments wait for the storage keys | `videos/06-sprint-4-finance-and-performance-user-manual.mp4` |
| S5 Intelligence & hardening | Advisory AI assistant, exports and advanced reports, accessibility, security and load pass, production cut-over | planned |

## Run locally
```
docker compose up -d                                   # PostgreSQL on localhost:15434
cd backend && python -m venv .venv && .venv/Scripts/pip install -r requirements.txt
set APP_ENV=demo && python -m app.seed --reset         # demo data (demo mode only)
python -m uvicorn app.main:app --port 8000             # serves the API and the built web app
cd ../frontend && npm install && npm run build         # or npm run dev (port 5173, proxies /api)
```
Demo sign-ins are listed under the Sign in button (shared disposable password, demo environment only). All data is fictional.

## Mobile app (Expo)
```
cd mobile && npm install
EXPO_PUBLIC_API_URL=http://localhost:8000 npx expo start      # scan with Expo Go; default API is the demo deployment
npx tsc --noEmit && npx expo export --platform web             # the checks used in CI here
```
The token is kept in memory only; use expo-secure-store before a store release.

## Tests
```
cd backend && python -m pytest tests -q               # needs the tracker_test database
cd videos && node check-screens.mjs                   # every persona signs in and opens every screen
```

## Deploy (Coolify)
`python deploy/coolify_deploy.py` reads `.env.coolify` (git-ignored, see `.env.coolify.example`) and creates/updates the Coolify resource from `docker-compose.coolify.yml`. Web `https://aadiprojecttracker.aaditechnology.com`, API `https://aadiprojecttrackerapi.aaditechnology.com`.

## Governance
Proposed defaults are not customer approvals. Revenue basis and the meaning of the S/H planning markers are stored as *undecided* until the customer decides.
