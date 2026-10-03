"""
Stage 03: Automatic Profiling & Compatibility
Inspects field data types, value ranges, missingness rates, repeated components,
and verifies mathematical eligibility for Anomaly Detection (IF) and Trajectory Forecasting (GPR).
"""
from .profiler import DatasetProfiler
AutoProfiler = DatasetProfiler  # Standard alias
from .compatibility import CompatibilityChecker

__all__ = [
    "DatasetProfiler",
    "AutoProfiler",
    "CompatibilityChecker",
]
