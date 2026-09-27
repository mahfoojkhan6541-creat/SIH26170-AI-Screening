from typing import Dict, Any
from src.decision.risk_fusion import RiskFusionEngine


class DecisionRuleEngine:
    """
    Evaluates fused evidence to produce controlled operational recommendations.
    Strictly enforces aerospace/ISRO screening protocol:
    1. Data Quality Failure -> RETEST (never scrap hardware on corrupt data)
    2. Common Mode Confounder -> REVIEW (prevent false rejection during chamber/test-fixture shifts)
    3. Multi-Parameter Discordance -> REVIEW / Watch-list
    4. Gross Deviation -> REJECT Candidate (Advisory only; AI never has final rejection authority)
    5. Nominal -> PASS (Recommended for Human QA milestone sign-off)
    """

    def __init__(self, review_threshold: float = 0.65, reject_threshold: float = 0.85):
        self.review_threshold = review_threshold
        self.reject_threshold = reject_threshold

    def evaluate(self, evidence_pack: Dict[str, Any]) -> Dict[str, Any]:
        fused = RiskFusionEngine.fuse_evidence(evidence_pack)

        base_governance = {
            "authority": "ADVISORY_ONLY",
            "requires_human_disposition": True,
            "final_rejection_authority": "HUMAN_QA_MANDATORY",
            "fused_evidence": fused
        }

        # Rule 1: RETEST - Data quality failure takes priority to avoid false rejection
        if fused["is_quality_compromised"]:
            return {
                **base_governance,
                "recommendation": "RETEST",
                "triggered_rule": "RULE_DATA_INTEGRITY_FAIL",
                "confidence": "HIGH",
                "action": "Order re-test or inspection of measurement contact/channel. Hardware must NEVER be condemned on untrusted or corrupted telemetry."
            }

        # Rule 2: REVIEW - Common mode takes priority over individual anomaly to prevent false reject
        if fused["is_common_mode"]:
            return {
                **base_governance,
                "recommendation": "REVIEW",
                "triggered_rule": "RULE_COMMON_MODE_CONFOUNDER",
                "confidence": "HIGH",
                "action": "Common-mode drift detected across multiple peer components. Inspect chamber/instrument calibration before isolating component."
            }

        # Rule 3: REJECT Candidate - Gross anomaly
        # AI never has final rejection authority: must be flagged for Human QA disposition
        if fused["is_high_anomaly"]:
            return {
                **base_governance,
                "recommendation": "REJECT",
                "triggered_rule": "RULE_CRITICAL_ANOMALY",
                "confidence": "HIGH",
                "action": "Flagged as candidate for rejection due to severe statistical/trajectory deviation. AI is advisory only; final hardware rejection requires certified Human QA disposition."
            }

        # Rule 4: REVIEW - Multi-parameter correlation discordance
        if fused.get("is_multi_param_anomaly", False):
            d_count = fused.get("discordant_pairs_count", 0)
            d_dist = fused.get("mahalanobis_distance", 0.0)
            return {
                **base_governance,
                "recommendation": "REVIEW",
                "triggered_rule": "RULE_MULTI_PARAM_DISCORDANCE",
                "confidence": "MODERATE",
                "action": f"Abnormal joint multi-parameter behavior detected ({d_count} discordant pair(s), Mahalanobis D_M={d_dist:.2f}). Route to engineering review."
            }

        # Rule 5: REVIEW - Moderate anomaly / forecast risk / wide uncertainty
        if fused["is_review_anomaly"] or fused["is_forecast_risky"] or fused["wide_uncertainty"]:
            reasons = []
            if fused["is_review_anomaly"]:
                reasons.append(f"Anomaly score ({fused['anomaly_score']:.3f}) exceeds review threshold ({self.review_threshold})")
            if fused["is_forecast_risky"]:
                reasons.append("Forecast projects adverse trajectory towards risk boundary")
            if fused["wide_uncertainty"]:
                reasons.append("Wide predictive uncertainty due to sparse trajectory history")

            return {
                **base_governance,
                "recommendation": "REVIEW",
                "triggered_rule": "RULE_ELEVATED_WATCH_LIST",
                "confidence": "MODERATE",
                "action": f"Route to QA engineering disposition: {'; '.join(reasons)}."
            }

        # Rule 6: PASS - Nominal screening
        return {
            **base_governance,
            "recommendation": "PASS",
            "triggered_rule": "RULE_NOMINAL_PASS",
            "confidence": "HIGH",
            "action": "Component behavior matches expected peer population baseline. Recommended for Human QA milestone sign-off."
        }
