"""
Stage 06: Confounder Handling & Common-Mode Detection
Monitors lot-to-lot manufacturing variance, test-chamber temperature shifts,
and sensor common-mode step changes affecting multiple components simultaneously.
"""
from .common_mode import CommonModeDetector
from .time_align import TimeAligner

__all__ = [
    "CommonModeDetector",
    "TimeAligner",
]
