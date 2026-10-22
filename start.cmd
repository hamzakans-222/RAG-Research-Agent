@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    python -m venv .venv
    if errorlevel 1 goto failed
)
set "PROJECT_PYTHON=%~dp0.venv\Scripts\python.exe"
"%PROJECT_PYTHON%" -m pip install -r requirements-web.txt
if errorlevel 1 goto failed
"%PROJECT_PYTHON%" scripts/setup_local.py
if errorlevel 1 goto failed
docker compose up -d --wait
if errorlevel 1 goto failed
"%PROJECT_PYTHON%" manage.py migrate --noinput
if errorlevel 1 goto failed
echo Memo est disponible sur http://127.0.0.1:8001 - Ctrl+C pour arreter.
"%PROJECT_PYTHON%" manage.py runserver 127.0.0.1:8001
exit /b %errorlevel%

:failed
echo Le demarrage a echoue. Consultez le message ci-dessus et verifiez que Docker Desktop est ouvert.
exit /b 1
