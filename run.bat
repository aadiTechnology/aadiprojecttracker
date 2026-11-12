@echo off
rem Starts Aadi Project Tracker for development on http://localhost:8000 (run setup.bat once first).
cd /d "%~dp0"
docker compose up -d postgres >nul 2>nul
cd backend
set APP_ENV=demo
set DATABASE_URL=postgresql+psycopg://tracker:tracker_dev@localhost:15434/tracker_aadi_test
.venv\Scripts\python.exe -m uvicorn app.main:app --port 8000 --reload
