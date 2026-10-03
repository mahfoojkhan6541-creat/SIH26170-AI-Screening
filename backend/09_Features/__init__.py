"""
Stage 09: Feature & Behavior Engineering
Constructs baseline delta, drift slope, curvature, volatility,
and peer-relative deviations (Z-score, MAD) without future-time leakage.
"""
from .baseline import BaselineFeatureExtractor
from .drift import DriftFeatureExtractor
from .peer_relative import PeerRelativeFeatureExtractor
from .engineering import FeatureEngineeringEngine

__all__ = [
    "BaselineFeatureExtractor",
    "DriftFeatureExtractor",
    "PeerRelativeFeatureExtractor",
    "FeatureEngineeringEngine",
]
