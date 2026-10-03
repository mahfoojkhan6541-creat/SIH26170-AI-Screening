from typing import Dict, Any, Optional
from backend.stage_06_confounders.common_mode import CommonModeDetector
from .multi_parameter import MultiParameterCorrelationDetector


class EvidenceGenerator:
    """Consolidates anomaly, forecast, data quality, peer, common-mode, and multi-parameter correlation evidence into an Evidence Pack."""

    @staticmethod
    def build_evidence_pack(
        component_id: str,
        checkpoint: Any,
        data_quality_info: Dict[str, Any],
        anomaly_info: Dict[str, Any],
        forecast_info: Optional[Dict[str, Any]],
        peer_evidence: Dict[str, Any],
        confounder_info: Optional[Dict[str, Any]] = None,
        multi_parameter_info: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        return {
            "component_id": str(component_id),
            "checkpoint": checkpoint,
            "data_quality": {
                "status": data_quality_info.get("status", "VALID"),
                "reasons": data_quality_info.get("reasons", "No quality issues detected")
            },
            "anomaly": {
                "score": float(anomaly_info.get("anomaly_score", 0.0)),
                "status": anomaly_info.get("anomaly_status", "normal"),
                "model_version": anomaly_info.get("model_version", "unknown"),
                "top_features": anomaly_info.get("top_features", [])
            },
            "forecast": {
                "status": forecast_info.get("forecast_status", "unavailable_insufficient_history") if forecast_info else "unavailable_insufficient_history",
                "mean": forecast_info.get("forecast_mean") if forecast_info else None,
                "std": forecast_info.get("forecast_std") if forecast_info else None,
                "interval": forecast_info.get("interval") if forecast_info else None,
                "horizon": forecast_info.get("forecast_horizon") if forecast_info else None
            },
            "peer_comparison": peer_evidence,
            "confounder": confounder_info or CommonModeDetector.get_nominal_evidence(checkpoint),
            "multi_parameter_correlation": multi_parameter_info or MultiParameterCorrelationDetector.get_nominal_evidence()
        }
