@echo off
title Screening AI - ISRO Aerospace QA Intelligence
echo ==============================================================================
echo Screening AI: AI-Driven Anomaly Detection in Component Burn-In & Screening
echo Starting Backend API and Clean White Aerospace Dashboard...
echo ==============================================================================

if exist venv\Scripts\python.exe (
    set PYTHON_EXEC=venv\Scripts\python.exe
) else (
    set PYTHON_EXEC=python
)

echo.
echo [1/2] Synchronizing authentic database and dashboard artifacts...
%PYTHON_EXEC% scripts\export_all_real_data.py

echo.
echo [2/2] Launching Uvicorn Server on http://localhost:8000 ...
echo - Dashboard UI:    http://localhost:8000/
echo - Swagger API:     http://localhost:8000/docs
echo - Health Check:    http://localhost:8000/health
echo ==============================================================================
echo.

%PYTHON_EXEC% -m uvicorn src.api.service:app --host 127.0.0.1 --port 8000 --reload
pause
