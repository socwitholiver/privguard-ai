@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo [PrivGuard Demo] Virtual environment not found at .venv\Scripts\python.exe
    echo [PrivGuard Demo] Create it first, then install dependencies.
    echo.
    echo Suggested setup:
    echo   py -3.10 -m venv .venv
    echo   .venv\Scripts\python.exe -m pip install -r requirements.txt
    exit /b 1
)

.venv\Scripts\python.exe scripts\rebuild_demo_workflow.py --target 500
if errorlevel 1 exit /b %errorlevel%

.venv\Scripts\python.exe app.py
exit /b %errorlevel%
