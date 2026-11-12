@echo off
rem First-time setup of Aadi Project Tracker on a developer machine (Windows). Safe to run again.
rem Needs: Python 3.12+, Node.js 20+ (for the web app), Docker Desktop (for PostgreSQL).
rem Result: database ready and the Aadi-Test company loaded from the Matrix workbook (15 people, 12 projects, salaries, allocations).
setlocal
cd /d "%~dp0"

where python >nul 2>nul || (echo Python is not installed or not on PATH. Install Python 3.12 or newer from python.org and run again. & exit /b 1)
where docker >nul 2>nul || (echo Docker is not installed. Install Docker Desktop and run again. & exit /b 1)
docker info >nul 2>nul || (echo Docker is installed but not running. Start Docker Desktop, wait until it says running, and run again. & exit /b 1)

echo Starting PostgreSQL (port 15434)...
docker compose up -d postgres || exit /b 1
set /a tries=0
:wait
docker compose exec -T postgres pg_isready -U tracker >nul 2>nul && goto ready
set /a tries+=1
if %tries% GEQ 40 (echo The database did not become ready. Run "docker compose logs postgres". & exit /b 1)
timeout /t 2 /nobreak >nul
goto wait
:ready
docker compose exec -T postgres psql -U tracker -d postgres -tc "SELECT 1 FROM pg_database WHERE datname='tracker_aadi_test'" | findstr 1 >nul || docker compose exec -T postgres psql -U tracker -d postgres -c "CREATE DATABASE tracker_aadi_test" || exit /b 1

cd backend
if not exist .venv (
  echo Creating the Python environment...
  python -m venv .venv || exit /b 1
)
echo Installing packages...
.venv\Scripts\python.exe -m pip install -q --disable-pip-version-check -r requirements.txt || exit /b 1

set APP_ENV=demo
set DATABASE_URL=postgresql+psycopg://tracker:tracker_dev@localhost:15434/tracker_aadi_test
echo Loading the Aadi-Test company...
.venv\Scripts\python.exe -m app.seed_aadi_test || exit /b 1
cd ..

where npm >nul 2>nul
if errorlevel 1 (
  echo Node.js was not found, so the web app was not built. Install Node.js 20+ and run setup.bat again, or use "npm run dev" in the frontend folder later.
) else (
  echo Building the web app...
  cd frontend
  call npm install --no-audit --no-fund || exit /b 1
  call npm run build || exit /b 1
  cd ..
)

echo.
echo Project Tracker is ready. Start it with run.bat, then open http://localhost:8000
echo Under the sign-in form every Aadi-Test person is listed; the password is AadiTest@2026.
endlocal
