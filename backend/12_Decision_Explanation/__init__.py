"""
Stage 12: Conservative Decision Rules & Explainable AI (XAI)
Operational recommendations: PASS (flight ready), RETEST (corrupt/noisy data),
REVIEW (marginal drift or common-mode confounder), and REJECT (severe defect candidate).
Outputs plain-English template explanations and TreeSHAP feature attributions.
"""
from .rules import DecisionRuleEngine
from .risk_fusion import RiskFusionEngine
from .explanation import ExplanationGenerator

__all__ = [
    "DecisionRuleEngine",
    "RiskFusionEngine",
    "ExplanationGenerator",
]
