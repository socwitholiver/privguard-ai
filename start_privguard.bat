@echo off
setlocal
cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" app.py
    exit /b %errorlevel%
)

echo [PrivGuard] Virtual environment not found at .venv\Scripts\python.exe
echo [PrivGuard] Create it first, then install dependencies.
echo.
echo Suggested setup:
echo   py -3.10 -m venv .venv
echo   .venv\Scripts\python.exe -m pip install -r requirements.txt
exit /b 1
