#!/usr/bin/env python3
"""
Legacy alias for scripts/export_all_real_data.py.
Redirects to the authentic SQLite and canonical pipeline exporter to guarantee zero synthetic data leakage.
"""
import sys
import os

sys.path.insert(0, os.path.abspath("."))
from scripts.export_all_real_data import export_workspace_and_dashboard_data

def generate_dashboard_data():
    print("[MIGRATED] scripts/build_rich_dashboard_data.py -> invoking authentic pipeline exporter: scripts/export_all_real_data.py")
    return export_workspace_and_dashboard_data()

if __name__ == "__main__":
    generate_dashboard_data()
