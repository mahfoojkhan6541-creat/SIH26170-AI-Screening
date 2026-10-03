"""
Stage 07: Canonical Internal Representation
Standardizes all heterogeneous burn-in streams into a unified,
traceable internal format preserving identity, measurement, temporal, and quality metadata.
"""
from .canonical import CanonicalTransformer

__all__ = [
    "CanonicalTransformer",
]
