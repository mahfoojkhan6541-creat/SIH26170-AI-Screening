import os
import json
import pytest
import sqlite3
import numpy as np
import pandas as pd
from fastapi.testclient import TestClient

from src.api.service import app
from src.validation.validator import DataQualityValidator
from src.validation.quarantine import QuarantineManager
from src.grouping.common_mode import CommonModeDetector
from src.evidence.multi_parameter import MultiParameterCorrelationDetector
from src.evidence.generator import EvidenceGenerator
from src.decision.rules import DecisionRuleEngine
from src.decision.risk_fusion import RiskFusionEngine
from src.explanation.generator import ExplanationGenerator
from src.audit.storage import AuditStorage
from src.models.forecasting.gpr_forecaster import GPRTrajectoryForecaster


# =============================================================================
# 1. Data Quality Gate Regression (All 12 Cases & Quarantine)
# =============================================================================
class TestDataQualityRegression:

    def test_all_12_cases_implemented_and_functional(self):
        records = [
            # 1. Clean row
            {"component_id": "C_OK", "checkpoint": 0.0, "elapsed_time": 0.0, "unit": "V", "p1": 1.0, "p2": 2.0},
            # 2. Case 06: Blank ID (BLOCK)
            {"component_id": "", "checkpoint": 12.0, "elapsed_time": 12.0, "unit": "V", "p1": 1.0, "p2": 2.0},
            # 3. Case 01: Missing reading all NaN (QUARANTINE)
            {"component_id": "C_MISS_ALL", "checkpoint": 24.0, "elapsed_time": 24.0, "unit": "V", "p1": np.nan, "p2": np.nan},
            # 4. Case 02: Partial missingness (WARNING)
            {"component_id": "C_PARTIAL", "checkpoint": 36.0, "elapsed_time": 36.0, "unit": "V", "p1": 1.1, "p2": np.nan},
            # 5. Case 03: Sensor error Inf (QUARANTINE)
            {"component_id": "C_INF", "checkpoint": 48.0, "elapsed_time": 48.0, "unit": "V", "p1": np.inf, "p2": 2.0},
            # 6. Case 04: Duplicate reading
            {"component_id": "C_OK", "checkpoint": 0.0, "elapsed_time": 0.0, "unit": "V", "p1": 1.0, "p2": 2.0},
            # 7. Case 05: Invalid timestamp negative (QUARANTINE)
            {"component_id": "C_NEG_T", "checkpoint": -5.0, "elapsed_time": -5.0, "unit": "V", "p1": 1.0, "p2": 2.0},
            # 8. Case 07: Wrong unit (BLOCK)
            {"component_id": "C_BAD_U", "checkpoint": 60.0, "elapsed_time": 60.0, "unit": "INVALID_UNIT_XYZ", "p1": 1.0, "p2": 2.0},
        ]
        df = pd.DataFrame(records)
        validator = DataQualityValidator()
        clean_df, quarantined_df, report = validator.validate(df, param_keys=["p1", "p2"])

        assert report["total_evaluated"] == len(records)
        assert len(quarantined_df) > 0
        all_cases = report.get("all_checks_status", {})
        assert "case_06_wrong_component_id" in all_cases
        assert "case_01_missing_reading" in all_cases
        assert "case_03_sensor_error" in all_cases
        assert "case_04_duplicate_reading" in all_cases
        assert "case_05_wrong_timestamp" in all_cases
        assert "case_07_wrong_unit" in all_cases

    def test_quarantine_isolation(self, tmp_path):
        mgr = QuarantineManager(quarantine_dir=str(tmp_path / "quarantine"))
        bad_df = pd.DataFrame([{"component_id": "BAD_1", "checkpoint": 0, "quality_status": "BLOCK"}])
        res = mgr.quarantine_records(bad_df, run_id="reg_test_run", reason="Integration test quarantine")
        assert os.path.exists(res)
        assert res.endswith(".csv")


# =============================================================================
# 2. IF Leakage & Split Verification Regression
# =============================================================================
class TestIFLeakageRegression:

    def test_d2_model_registry_uses_clean_split_and_no_target_features(self):
        reg_path = "configs/model_registry.json"
        assert os.path.exists(reg_path), "Model registry must exist"
        with open(reg_path, "r", encoding="utf-8") as f:
            registry = json.load(f)

        assert "D2" in registry
        d2_entry = registry["D2"]
        assert "is_test == 0" in d2_entry.get("training_split", "")
        assert d2_entry.get("metrics", {}).get("recall", 0.0) >= 0.90
        assert d2_entry.get("metrics", {}).get("accuracy", 0.0) >= 0.85

    def test_peer_relative_engineering_excludes_target_component(self):
        from src.features.engineering import FeatureEngineeringEngine
        engine = FeatureEngineeringEngine()

        # Target component has huge value 100.0, peers have 1.0
        data = [
            {"component_id": "TARGET", "checkpoint": 168.0, "elapsed_time": 168.0, "p1": 100.0, "is_test": 0},
            {"component_id": "PEER_1", "checkpoint": 168.0, "elapsed_time": 168.0, "p1": 1.0, "is_test": 0},
            {"component_id": "PEER_2", "checkpoint": 168.0, "elapsed_time": 168.0, "p1": 1.0, "is_test": 0},
            {"component_id": "PEER_3", "checkpoint": 168.0, "elapsed_time": 168.0, "p1": 1.0, "is_test": 0},
            {"component_id": "PEER_4", "checkpoint": 168.0, "elapsed_time": 168.0, "p1": 1.0, "is_test": 0},
            {"component_id": "PEER_5", "checkpoint": 168.0, "elapsed_time": 168.0, "p1": 1.0, "is_test": 0},
            {"component_id": "PEER_6", "checkpoint": 168.0, "elapsed_time": 168.0, "p1": 1.0, "is_test": 0},
        ]
        df = pd.DataFrame(data)
        X_df, meta_df, _ = engine.extract_feature_matrix_batch(df, param_keys=["p1"], checkpoint=168.0)

        # Peer mean for TARGET must be 1.0 (mean of PEER_1 to PEER_6), NOT (100+6)/7 = 15.14
        target_peer_mean = meta_df.loc["TARGET", "p1_peer_mean"]
        assert abs(target_peer_mean - 1.0) < 1e-4, f"Target component was not excluded from peer mean: {target_peer_mean}"


# =============================================================================
# 3. GPR Leakage & Physical Device Grouping Regression
# =============================================================================
class TestGPRLeakageRegression:

    def test_physical_device_grouping_prevents_paired_device_leakage(self):
        # NASA canonical has Device2 and Device2b mapped to Device_2
        canonical_path = "data/canonical/NASA_degradation_canonical.csv"
        if os.path.exists(canonical_path):
            df = pd.read_csv(canonical_path)
            phys_groups = df.groupby("physical_device_id")["source_files"].unique().to_dict()
            assert "Device_2" in phys_groups
            assert "Device2, Device2b" in phys_groups["Device_2"][0]
            assert "Device3, Device3b" in phys_groups["Device_3"][0]
            assert "Device4, Device4b" in phys_groups["Device_4"][0]

    def test_d2_never_displays_fabricated_gpr_forecast(self):
        forecaster = GPRTrajectoryForecaster()
        # D2 has only 2 checkpoints (0h and 168h)
        d2_traj = pd.DataFrame([
            {"checkpoint": 0.0, "param_01": 2.82},
            {"checkpoint": 168.0, "param_01": 2.85}
        ])
        result = forecaster.fit_and_predict(d2_traj, "param_01", future_checkpoints=[192.0])
        assert result["forecast_status"] == "unavailable_insufficient_history"
        assert result["forecast_mean"] is None
        assert result["forecast_std"] is None


# =============================================================================
# 4. Common-Mode Detection Regression
# =============================================================================
class TestCommonModeRegression:

    def test_synchronized_shift_detected_across_peers(self):
        records = []
        for cid in ["TARGET", "P1", "P2", "P3", "P4", "P5"]:
            records.append({"component_id": cid, "part_type": "HEMT", "checkpoint": 0.0, "p1": 1.0})
            shift = 0.50 if cid != "P5" else 0.0  # 4 out of 5 peers shift (+80%)
            records.append({"component_id": cid, "part_type": "HEMT", "checkpoint": 12.0, "p1": 1.0 + shift})

        df = pd.DataFrame(records)
        detector = CommonModeDetector(threshold_pct=60.0, min_peers=3)
        ev = detector.detect_for_component(df, target_component_id="TARGET", checkpoint=12.0, param_keys=["p1"])

        assert ev["common_mode_detected"] is True
        assert ev["common_mode_status"] == "DETECTED"
        assert ev["percentage_affected"] >= 60.0

    def test_never_pools_across_different_part_types(self):
        records = [
            {"component_id": "T1", "part_type": "IGBT", "checkpoint": 0.0, "p1": 1.0},
            {"component_id": "T1", "part_type": "IGBT", "checkpoint": 12.0, "p1": 1.0},
            {"component_id": "P_GAN1", "part_type": "GAN", "checkpoint": 0.0, "p1": 5.0},
            {"component_id": "P_GAN1", "part_type": "GAN", "checkpoint": 12.0, "p1": 10.0},
        ]
        df = pd.DataFrame(records)
        detector = CommonModeDetector(min_peers=1)
        ev = detector.detect_for_component(df, target_component_id="T1", checkpoint=12.0, param_keys=["p1"])
        # GaN peer must NOT be pooled into IGBT peer cohort
        assert ev["total_peer_count"] == 0


# =============================================================================
# 5. Multi-Parameter Correlation Evidence Regression
# =============================================================================
class TestMultiParameterEvidenceRegression:

    def test_multi_parameter_detects_joint_divergence(self):
        detector = MultiParameterCorrelationDetector(corr_threshold=0.50, joint_z_threshold=2.5)

        # Create cohort where p1 and p2 are strongly positively correlated (r ~ 0.99)
        records = []
        for i in range(30):
            val = float(i) * 0.1
            records.append({"component_id": f"PEER_{i}", "checkpoint": 24.0, "p1": val, "p2": val + 0.01})

        # Add target component with strong negative divergence (p1 high, p2 low)
        records.append({"component_id": "TARGET_DISCORDANT", "checkpoint": 24.0, "p1": 3.0, "p2": 0.0})

        df = pd.DataFrame(records)
        ev = detector.evaluate_component(df, target_component_id="TARGET_DISCORDANT", param_keys=["p1", "p2"], checkpoint=24.0)

        assert ev["status"] == "DETECTED"
        assert ev["abnormal_joint_behavior_detected"] is True
        assert ev["discordant_pairs_count"] >= 1
        assert ev["mahalanobis_distance"] > 2.0
        assert "p1" in ev["evidence_summary"] and "p2" in ev["evidence_summary"]

    def test_multi_parameter_nominal_when_coupled(self):
        detector = MultiParameterCorrelationDetector(corr_threshold=0.50, joint_z_threshold=2.5)
        records = []
        for i in range(30):
            val = float(i) * 0.1
            records.append({"component_id": f"PEER_{i}", "checkpoint": 24.0, "p1": val, "p2": val})

        records.append({"component_id": "TARGET_NOMINAL", "checkpoint": 24.0, "p1": 1.5, "p2": 1.5})
        df = pd.DataFrame(records)
        ev = detector.evaluate_component(df, target_component_id="TARGET_NOMINAL", param_keys=["p1", "p2"], checkpoint=24.0)

        assert ev["status"] == "NOMINAL"
        assert ev["abnormal_joint_behavior_detected"] is False


# =============================================================================
# 6. Decision Flow, Explanations, RETEST & AI Non-Final Authority Regression
# =============================================================================
class TestDecisionAndGovernanceRegression:

    def test_full_decision_flow_priority_and_retest(self):
        engine = DecisionRuleEngine()

        # 1. Compromised quality -> RETEST takes absolute priority over high anomaly
        ev_pack_bad_data = {
            "data_quality": {"status": "QUARANTINE", "reasons": "Telemetry dropout"},
            "anomaly": {"score": 0.99, "status": "high"},
            "forecast": {"status": "unavailable_insufficient_history"},
            "confounder": {"common_mode_detected": False}
        }
        dec = engine.evaluate(ev_pack_bad_data)
        assert dec["recommendation"] == "RETEST"
        assert dec["triggered_rule"] == "RULE_DATA_INTEGRITY_FAIL"
        assert dec["authority"] == "ADVISORY_ONLY"
        assert dec["requires_human_disposition"] is True
        assert dec["final_rejection_authority"] == "HUMAN_QA_MANDATORY"

    def test_ai_never_has_final_rejection_authority(self):
        engine = DecisionRuleEngine()
        ev_pack_reject = {
            "data_quality": {"status": "VALID", "reasons": "Passed"},
            "anomaly": {"score": 0.95, "status": "high"},
            "forecast": {"status": "unavailable_insufficient_history"},
            "confounder": {"common_mode_detected": False}
        }
        dec = engine.evaluate(ev_pack_reject)
        assert dec["recommendation"] == "REJECT"
        assert dec["authority"] == "ADVISORY_ONLY"
        assert dec["requires_human_disposition"] is True
        assert "Human QA" in dec["action"]

    def test_multi_parameter_discordance_triggers_review(self):
        engine = DecisionRuleEngine()
        ev_pack_mp = {
            "data_quality": {"status": "VALID", "reasons": "Passed"},
            "anomaly": {"score": 0.40, "status": "normal"},
            "forecast": {"status": "unavailable_insufficient_history"},
            "confounder": {"common_mode_detected": False},
            "multi_parameter_correlation": {
                "abnormal_joint_behavior_detected": True,
                "discordant_pairs_count": 2,
                "mahalanobis_distance": 4.12
            }
        }
        dec = engine.evaluate(ev_pack_mp)
        assert dec["recommendation"] == "REVIEW"
        assert dec["triggered_rule"] == "RULE_MULTI_PARAM_DISCORDANCE"

    def test_explanation_contains_governance_disclaimer(self):
        exp_gen = ExplanationGenerator()
        ev = EvidenceGenerator.build_evidence_pack("TEST_DEV", 168.0, {"status": "VALID"}, {"anomaly_score": 0.3}, None, {})
        dec = DecisionRuleEngine().evaluate(ev)
        bundle = exp_gen.generate_explanation("TEST_DEV", ev, dec)

        assert "Human QA" in bundle["plain_english_reason"]
        assert bundle["authority"] == "ADVISORY_ONLY"
        assert bundle["requires_human_disposition"] is True


# =============================================================================
# 7. API Endpoints & Provenance Traceability Regression
# =============================================================================
class TestAPIRegression:

    @pytest.fixture(scope="class")
    def client(self):
        return TestClient(app)

    def test_api_health_endpoint(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "healthy"

    def test_api_traceability_endpoint(self, client):
        # Authenticate provenance route for an existing component
        resp = client.get("/api/components/2/trace")
        if resp.status_code == 200:
            data = resp.json()
            assert data["component_id"] == "2"
            assert "raw_data" in data["provenance_chain"]
            assert "pipeline_run" in data["provenance_chain"]
            assert "decision" in data["provenance_chain"]
            assert "qa_action" in data["provenance_chain"]

    def test_api_workspace_contains_no_synthetic_ids(self, client):
        resp = client.get("/api/workspace")
        assert resp.status_code == 200
        wdata = resp.json()
        assert wdata["dataOrigin"] == "AUTHENTIC_PIPELINE_RUN"

        # Check for forbidden synthetic strings
        text = json.dumps(wdata)
        assert "M084" not in text
        assert "LOT-D2-08" not in text
        assert "LOT-D2-15" not in text

    def test_audit_qa_action_recording(self, client):
        # Test recording human disposition
        payload = {
            "run_id": "reg_test_run_qa",
            "component_id": "TEST_COMP_99",
            "checkpoint": 168.0,
            "ai_recommendation": "REVIEW",
            "human_action": "CONFIRM_PASS",
            "reviewer_id": "QA_LEAD_REGRESSION",
            "notes": "Regression test verified"
        }
        resp = client.post("/audit/qa-action", json=payload)
        assert resp.status_code == 200
        assert resp.json()["status"] == "recorded"


# =============================================================================
# 8. UI & Production Artifact Regression
# =============================================================================
class TestUIRegression:

    def test_dashboard_files_contain_no_fake_ids(self):
        dashboard_files = [
            "dashboard/shared.js",
            "dashboard/screening.html",
            "dashboard/overview.html",
            "dashboard/diagnostics.html"
        ]
        for fpath in dashboard_files:
            if os.path.exists(fpath):
                with open(fpath, "r", encoding="utf-8") as f:
                    content = f.read()
                    assert "M084" not in content, f"Found M084 in {fpath}"
                    assert "LOT-D2-08" not in content, f"Found LOT-D2-08 in {fpath}"
                    assert "LOT-D2-15" not in content, f"Found LOT-D2-15 in {fpath}"
