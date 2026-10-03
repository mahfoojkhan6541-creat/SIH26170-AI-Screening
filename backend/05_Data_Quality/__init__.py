"""
Stage 05: Data Quality + Identity + Time Gate
Executes the strict 12-check aerospace quality gate decomposition:
missing readings, sensor saturation, NaN/Inf, identity integrity,
and isolates corrupted or untrusted observations in quarantine storage.
"""
from .validator import DataQualityValidator
from .quarantine import QuarantineManager

__all__ = [
    "DataQualityValidator",
    "QuarantineManager",
]
