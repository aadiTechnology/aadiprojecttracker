# Aadi Identity Platform: Extraction Sprint Plan

Extract authentication, tenants and product subscriptions out of Project Tracker into an independently hosted **Identity Platform**. Project Tracker is the first product on it. DMS, CRM and Aadi Social follow one at a time.

Status: proposal for review. Sprint length assumed at two weeks. Based on a read of Project Tracker's `core.py`, `models.py`, `tenancy.py` and the `auth` and `platform` routers; CRM and Social code were not inspected.

## 1. Principles

1. **Product features do not change.** Only where the sign-in comes from changes.
2. **Project Tracker keeps its architecture.** Its database, tenant tables, roles and permission checks stay. It gains a way to accept a platform token and map it to its local user and tenant.
3. **Identity decides who you are, which companies you belong to and which products they bought.** Each product still decides what you can do inside it, using its own roles (decision D3 can revisit this later).
4. **Dual mode.** `AUTH_MODE=local | platform` per environment. Local mode is today's behaviour and is the rollback path.
5. **One product at a time.** Nothing in Sprint 1 to 5 requires another product to change.
6. **Standards, not custom protocol.** OIDC authorization code with PKCE, RS256 signed tokens, a JWKS endpoint.

## 2. What exists today in Project Tracker (extraction scope)

| Concern | Where | Becomes |
|---|---|---|
| Login, lockout, password hash (Argon2) | `routers/auth.py` `/auth/login`, `core.py` | Identity service |
| Forgot / reset password, invitations | `/auth/forgot`, `/auth/reset`, `tenancy.py`, `mail.py` | Identity service (mail sent from Identity) |
| Tenant switch | `/auth/switch` | Identity chooser and switcher |
| Revoke all sessions (`token_epoch`) | `/auth/logout-all`, `core.py` | Identity session store plus a revocation signal |
| JWT issue and decode (HS256, shared secret) | `core.py` `issue_jwt`, `_decode` | Identity issues RS256; Project Tracker verifies via JWKS |
| Users, tenants | `models.py` `User`, `Tenant` | Identity owns the master; Project Tracker keeps a local mirror |
| Memberships, roles, permissions | `models.py` `Membership`, `Role`, `perms.py` | **Stay in Project Tracker** |
| Module entitlements inside Project Tracker | `Entitlement`, `/platform/tenants/.../modules` | Stay; product-level subscription moves to Identity |
| Platform admin (tenant create, suspend) | `routers/platform.py` | Moves to Identity admin; Project Tracker keeps a thin sync |
| Web token storage | `frontend/src/api.ts` (`sessionStorage`) | Replaced by OIDC redirect plus Project Tracker's own short session |

## 3. Target architecture

```
Browser ──► id.aadi.app  (Identity Platform: API + login UI, own database)
              │  login · tenant list · product list · switcher · admin
              │  issues ID token + access token (RS256), publishes JWKS
              ▼
        redirect with code ──► tracker.aadi.app (Project Tracker, unchanged domain logic)
                                  verifies token with JWKS
                                  maps identity_id → local User, identity_tenant_id → local Tenant
                                  applies its own Role/permissions
```

**Redirect rule (the single-product requirement):** after authentication the Identity service computes the user's eligible (tenant, product) pairs.
- 0 pairs: "no active subscription" page.
- 1 pair: redirect straight to that product. No chooser is shown.
- More than 1: chooser, remembering the last choice.

**Identity data model (new database):** `users`, `credentials`, `tenants`, `tenant_members`, `products`, `subscriptions` (tenant, product, status, seats, valid_until), `sessions`, `auth_tokens` (invite, reset), `audit_log`, `signing_keys`.

**Project Tracker additions (additive only):** `users.identity_id`, `tenants.identity_tenant_id`, an OIDC callback route, a token verifier next to the existing one, and a feature flag. No tables dropped.

## 4. Decisions needed before Sprint 1

| ID | Decision | Recommendation |
|---|---|---|
| D1 | Build the Identity service on Project Tracker's auth code, or adopt Keycloak/Ory | Build thin (FastAPI), reuse Argon2, lockout and token logic. Revisit if SSO/SAML becomes a requirement. |
| D2 | Hosting and domains | Subdomains of one parent domain (`id.`, `tracker.`, later `dms.`). Same host stack as Project Tracker (Docker, Coolify). |
| D3 | Where product roles are managed | Phase 1: inside each product, unchanged. Central role mapping is a later option. |
| D4 | Identifier strategy | Identity uses UUIDs. Products store the UUID next to their local ID. |
| D5 | Token lifetime and revocation | Access 15 min, refresh rotated, revocation event plus short lifetime. |
| D6 | Existing users with several tenants | Same email is one identity with several `tenant_members` rows. |

## 5. Sprints

### Sprint 0: Design and scaffolding (1 week)
**Goal:** decisions made, repository and pipeline ready, nothing user-visible.
- Resolve D1 to D6; write ADRs.
- Repository `aadi-identity` (FastAPI, SQLAlchemy 2, Alembic, PostgreSQL 16), CI, Dockerfile, Coolify compose.
- Contract document: OIDC endpoints, token claims, event names, error codes.
- Test plan: freeze Project Tracker's current test suite (72 backend tests plus web and a11y checks) as the regression baseline.

**Exit:** ADRs approved, empty service deploys, Project Tracker tests green on the baseline tag.

### Sprint 1: Identity core and data import
**Goal:** Identity can authenticate a user and knows tenants and subscriptions. Project Tracker untouched.
- Schema and migrations for the Identity data model.
- Password login with Argon2, lockout (5 failures, 15 minutes), same-message errors, rate limit.
- Sessions, refresh rotation, logout, logout-all.
- Forgot/reset and invitation flows (move logic and email templates from `auth.py`, `tenancy.py`, `mail.py`).
- RS256 key generation and rotation, `/.well-known/jwks.json`, `/.well-known/openid-configuration`.
- **Import tool:** reads Project Tracker's `users`, `tenants`, `memberships` into Identity. Idempotent, dry-run mode, mapping report. Passwords carry over as hashes (same algorithm, no reset needed).
- Seed `products` (Project Tracker) and one `subscriptions` row per existing tenant.

**Exit:** all existing Project Tracker demo users can sign in at Identity; import report shows zero unmatched users; security tests (lockout, enumeration, replay) pass.

### Sprint 2: OIDC flow, chooser and single-product redirect
**Goal:** the sign-in experience described in the requirement.
- Authorization code with PKCE, client registration for Project Tracker (`redirect_uris`, `post_logout_redirect_uris`).
- Login UI (web, responsive), chooser for multiple tenants/products, remember last choice.
- **Eligible-products resolver and redirect rule** (0, 1 or many).
- Product switcher API (`/me/products`) for the header menu.
- Global sign-out (front and back channel).
- A tiny test client app to prove the flow before touching Project Tracker.

**Exit:** with the test client, one-product users land directly in the product; multi-product users see the chooser; switching needs no password; accessibility sweep passes on the new screens.

### Sprint 3: Project Tracker on platform mode
**Goal:** Project Tracker accepts platform sign-in with every feature unchanged.
- Add `identity_id` and `identity_tenant_id` columns (Alembic, nullable, backfilled from the import).
- Token verifier using JWKS; `ctx()` gains a platform branch next to the current one. Permission code in `perms.py` is not touched.
- Local mapping: identity user to local `User`, identity tenant to local `Tenant`, then existing `Membership` and `Role` apply as today.
- First-login provisioning rule: if the identity is a member of the tenant in Identity but has no local `Membership`, deny with a clear message (no silent role grant).
- Web app: replace Login screen with redirect to Identity when `AUTH_MODE=platform`; token handling in `api.ts`; header switcher entry; logout goes to Identity.
- Mobile app (Expo): OIDC with PKCE through the system browser.
- Local mode untouched and still tested in CI (matrix: both modes).

**Exit:** the entire existing backend suite passes in both modes; web e2e journeys for every role pass in platform mode; mobile sign-in works; rollback by flag tested.

### Sprint 4: Admin, subscriptions and sync
**Goal:** operators can run the platform without touching Project Tracker.
- Identity admin: create tenant, invite owner, suspend tenant, grant or revoke product subscription, view audit.
- Move tenant creation/suspension out of `routers/platform.py` into Identity; Project Tracker receives `tenant.created/suspended` and `membership.changed` events (webhook or queue) and keeps its mirror correct.
- User lifecycle: deactivate user in Identity blocks all products within the token lifetime; immediate revoke via event.
- Nightly reconcile job comparing Identity and Project Tracker mirrors, with a report.
- Customer-facing company admin: invite employees, remove access, with audit entries on both sides.

**Exit:** create a tenant in Identity, sign in to Project Tracker as its owner, invite an employee, suspend and reactivate, all with no Project Tracker admin action; reconcile report is clean.

### Sprint 5: Hardening, migration and cut-over
**Goal:** production-ready and migrated.
- Security review (token validation, redirect URI allow-list, CSRF/state/nonce, key rotation drill, brute-force and enumeration tests).
- Load check (extend `backend/loadtest.py`), backup and restore of the Identity database, monitoring and alerts.
- Production runbook (extend `Production_Cutover_Runbook.md`): migrate one pilot tenant, then in batches; rollback steps.
- Retire local login screens only after a stable period; keep local mode available behind the flag.
- Documentation: **Product Onboarding Guide** (see section 6).

**Exit:** all tenants on platform mode with no regression tickets for a full release cycle; runbook rehearsed on staging.

### Sprint 6 (follow-on): DMS onboarding
Run the onboarding guide against DMS: register client, JWKS verifier in its `get_principal`, map identity UUID to its UUID user table, tenant mapping into its RLS context, dual mode flag. DMS already uses UUIDs and tenant context from the principal, so this is the smallest change. A DMS-only tenant lands directly in DMS.

## 6. Product Onboarding Guide (written in Sprint 5, used for every later product)

1. Register an OIDC client with the Identity service.
2. Add `identity_id` and `identity_tenant_id` to the product's user and tenant tables.
3. Verify tokens with JWKS; map to the local user and tenant; keep local roles and permissions.
4. Subscribe to `tenant.*`, `membership.*` and `user.*` events.
5. Add the header switcher component and global logout.
6. Add `AUTH_MODE` flag and run the product's test suite in both modes.
7. Pilot one tenant, then migrate in batches.

## 7. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Lockout of all users if Identity is down | Identity high-availability plan; token lifetime long enough to ride out short outages; local mode as emergency fallback for a pilot period. |
| User/tenant mismatch during import | Dry-run reports, idempotent import, reconcile job, no deletion in Project Tracker. |
| Same email, different people across products | Match on verified email; conflicts listed for manual resolution before cut-over. |
| Role drift between Identity and product | Phase 1 keeps roles in the product; Identity carries only membership. |
| Mobile sign-in redirect complexity | Prototype PKCE flow with Expo in Sprint 2, not Sprint 3. |
| Scope creep into product features | Rule: any change to product behaviour other than sign-in needs a separate ticket. |

## 8. Definition of done (every sprint)

- Existing Project Tracker tests pass in local mode.
- New tests for the sprint's scope pass.
- Security checks for the sprint pass; no secrets in the repository.
- Demo video or recorded walkthrough, as in earlier sprints.
- Rollback step documented.
