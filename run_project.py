#!/usr/bin/env python3
"""
Screening AI Unified Project Launcher
Launches the FastAPI backend and serves the Clean White Aerospace QA Dashboard.
"""
import os
import sys
import subprocess

def main():
    print("=" * 78)
    print("Screening AI: AI-Driven Anomaly Detection in Component Burn-In & Screening")
    print("=" * 78)

    # Use virtual environment python if available
    venv_py = os.path.join("venv", "Scripts", "python.exe") if os.name == "nt" else os.path.join("venv", "bin", "python")
    py_exec = venv_py if os.path.exists(venv_py) else sys.executable

    print("\n[1/2] Synchronizing authentic database and dashboard artifacts...")
    subprocess.run([py_exec, "scripts/export_all_real_data.py"], check=True)

    print("\n[2/2] Launching Uvicorn Server on http://localhost:8000 ...")
    print("  -> Dashboard UI:    http://localhost:8000/ or http://localhost:8000/dashboard/")
    print("  -> Swagger API:     http://localhost:8000/docs")
    print("  -> Health Check:    http://localhost:8000/health")
    print("=" * 78 + "\n")

    subprocess.run([py_exec, "-m", "uvicorn", "src.api.service:app", "--host", "127.0.0.1", "--port", "8000", "--reload"])

if __name__ == "__main__":
    main()
