"""
Stage 10: AI Model Branches
Two distinct aerospace-grade model branches:
  10A: Calibrated Isolation Forest for instantaneous & behavioral trajectory anomaly scoring.
  10B: Gaussian Process Regression (GPR) for long-horizon degradation forecasting with Bayesian uncertainty bounds.
"""
from .anomaly.isolation_forest import IsolationForestAnomalyDetector
from .forecasting.gpr_forecaster import GPRTrajectoryForecaster
from .evaluation import ModelEvaluator

__all__ = [
    "IsolationForestAnomalyDetector",
    "GPRTrajectoryForecaster",
    "ModelEvaluator",
]
