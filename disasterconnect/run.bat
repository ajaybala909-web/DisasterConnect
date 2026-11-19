@echo off
cd /d "%~dp0"
where py >nul 2>nul && (set PY=py) || (set PY=python)
if not exist venv (
  echo Setting up for the first time, please wait...
  %PY% -m venv venv || (echo Python is not installed. Get it from python.org and tick "Add to PATH". & pause & exit /b)
  venv\Scripts\python -m pip install -q -r requirements.txt
)
venv\Scripts\python app.py
pause
