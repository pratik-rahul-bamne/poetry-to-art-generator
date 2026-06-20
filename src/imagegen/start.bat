@echo off
TITLE ImageGen AI — Startup
color 0A

echo.
echo  ╔══════════════════════════════════════════════════════════╗
echo  ║          ImageGen AI — Local Stable Diffusion            ║
echo  ║         Powered by Stable Diffusion 1.5 (CPU)            ║
echo  ╚══════════════════════════════════════════════════════════╝
echo.

:: Navigate to script folder
cd /d "%~dp0"

:: Use the parent project's venv (already has torch, diffusers, etc.)
set VENV_PYTHON=..\..venv\Scripts\python.exe
set VENV_PIP=..\.venv\Scripts\pip.exe

:: Fallback: check if parent venv exists, else use imagegen venv
if not exist "..\.venv\Scripts\python.exe" (
    echo  [SETUP] Parent venv not found, creating local venv...
    python -m venv .venv
    set VENV_PYTHON=.venv\Scripts\python.exe
    set VENV_PIP=.venv\Scripts\pip.exe
    .venv\Scripts\pip.exe install -r requirements.txt -q
) else (
    echo  [INFO] Using existing project venv with torch + diffusers
    set VENV_PYTHON=..\.venv\Scripts\python.exe
    set VENV_PIP=..\.venv\Scripts\pip.exe
)

:: Create outputs dir
if not exist "backend\outputs" mkdir backend\outputs

echo.
echo  ✅ Starting ImageGen AI server...
echo  🌐 Open your browser at: http://localhost:8000
echo  🛑 Press Ctrl+C to stop
echo.

:: Open browser after 3 seconds
start /b cmd /c "timeout /t 3 /nobreak >nul && start http://localhost:8000"

:: Start backend using the correct python
cd backend
%VENV_PYTHON% -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload

pause
