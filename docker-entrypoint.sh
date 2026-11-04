#!/bin/sh
# Migrations run when the app starts. Demo data is loaded only when APP_ENV=demo and APP_SEED_DEMO=true (never in production).
set -e
if [ "$APP_SEED_DEMO" = "true" ]; then
  if [ "$APP_ENV" != "demo" ]; then echo "APP_SEED_DEMO=true requires APP_ENV=demo"; exit 1; fi
  python -c "from app.main import migrate; migrate()"
  python -m app.seed
fi
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips="*"
