@echo off
title HSN Code Classifier — Agentic Workflow
echo.
echo  ╔══════════════════════════════════════════════════════╗
echo  ║     HSN Code Classifier — Agentic Workflow v1.0     ║
echo  ║         Powered by Gemma 4 31B + RAG + GRI          ║
echo  ╚══════════════════════════════════════════════════════╝
echo.

cd /d "%~dp0"

echo [1/3] Checking Python...
python --version
if errorlevel 1 (
    echo ERROR: Python not found. Please install Python 3.10+
    pause
    exit /b 1
)

echo.
echo [2/3] Installing dependencies...
pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)

echo.
echo [3/3] Starting server...
echo.
echo   Open http://127.0.0.1:8899 in your browser
echo   Press Ctrl+C to stop
echo.

cd backend
python server.py
pause
