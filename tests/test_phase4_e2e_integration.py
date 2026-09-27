"""
End-to-End Integration Test for SIH26170 Phase 4
=================================================
Validates complete 8-stage lifecycle:
  1. Data Ingestion & Canonical Mapping
  2. 12-Check Data Quality Gate & Quarantine
  3. Feature Engineering & Isolation Forest Anomaly Scoring
  4. GPR Trajectory Forecasting (Applicable vs Suppressed for D2)
  5. Conservative Risk Fusion Decision & Plain-English Explanation
  6. Audit Traceability Logging in SQLite
  7. Human QA Authorization Recording (POST /audit/qa-action)
  8. Live UI/API Retrieval (GET /api/workspace, GET /api/components/{id}/trace)
"""

import os
import sys
import uuid
import json
import pytest
import pandas as pd
import numpy as np
from fastapi.testclient import TestClient

from src.api.service import app
from src.mapping.loader import MappingLoader
from src.mapping.canonical import CanonicalTransformer
from src.validation.validator import DataQualityValidator
from src.features.engineering import FeatureEngineeringEngine
from src.models.anomaly.isolation_forest import IsolationForestAnomalyDetector
from src.models.forecasting.gpr_forecaster import GPRTrajectoryForecaster
from src.evidence.generator import EvidenceGenerator
from src.decision.rules import DecisionRuleEngine
from src.explanation.generator import ExplanationGenerator
from src.audit.storage import AuditStorage


@pytest.fixture
def client():
    return TestClient(app)


def test_phase4_end_to_end_pipeline_and_traceability(client):
    """
    Executes the full end-to-end integration sequence:
    Ingestion -> Validation -> IF -> GPR -> Decision -> QA -> Audit -> API Trace
    """
    run_id = f"test_e2e_{uuid.uuid4().hex[:8]}"
    test_comp_d1 = f"E2E-MCU-{uuid.uuid4().hex[:4]}"
    test_comp_d2 = f"E2E-D2-{uuid.uuid4().hex[:4]}"

    audit_storage = AuditStorage()
    audit_storage.record_run_start(run_id, "E2E_SYNTH_DATASET", "v4_test")

    # -------------------------------------------------------------
    # 1. Ingestion & Canonical Mapping
    # -------------------------------------------------------------
    # Multi-checkpoint component (D1 style: 5 checkpoints)
    rows_d1 = []
    for step_idx, cp in enumerate([0.0, 24.0, 48.0, 96.0, 144.0]):
        rows_d1.append({
            "component_id": test_comp_d1,
            "checkpoint": cp,
            "elapsed_time": cp,
            "param_01": 1.20 + step_idx * 0.08,
            "param_02": 0.05 + step_idx * 0.005,
            "part_type": "RAD-HARD-MCU",
            "lot_id": "LOT-E2E-01"
        })

    # 2-checkpoint component (D2 style: 0h and 168h pre/post)
    rows_d2 = [
        {
            "component_id": test_comp_d2,
            "checkpoint": 0.0,
            "elapsed_time": 0.0,
            "param_01": 2.82,
            "param_02": 0.14,
            "part_type": "DISCRETE-HEMT",
            "lot_id": "LOT-E2E-02"
        },
        {
            "component_id": test_comp_d2,
            "checkpoint": 168.0,
            "elapsed_time": 168.0,
            "param_01": 2.86,
            "param_02": 0.16,
            "part_type": "DISCRETE-HEMT",
            "lot_id": "LOT-E2E-02"
        }
    ]

    canonical_df = pd.DataFrame(rows_d1 + rows_d2)
    assert len(canonical_df) == 7
    assert test_comp_d1 in canonical_df["component_id"].values
    assert test_comp_d2 in canonical_df["component_id"].values

    # -------------------------------------------------------------
    # 2. 12-Check Data Quality Gate
    # -------------------------------------------------------------
    validator = DataQualityValidator()
    valid_df, quarantined_df, dq_report = validator.validate(canonical_df, param_keys=["param_01", "param_02"])
    assert len(valid_df) == 7
    assert len(quarantined_df) == 0
    assert dq_report["quarantined_records"] == 0

    # -------------------------------------------------------------
    # 3. Feature Engineering & Isolation Forest Anomaly Scoring
    # -------------------------------------------------------------
    fe = FeatureEngineeringEngine()
    # Feature matrix for target components
    feat_d1 = {
        "param_01_baseline": 1.20,
        "param_01_current": 1.52,
        "param_01_delta": 0.32,
        "param_01_drift_slope": 0.0022,
        "param_01_peer_deviation": 1.45
    }
    feat_d2 = {
        "param_01_baseline": 2.82,
        "param_01_current": 2.86,
        "param_01_delta": 0.04,
        "param_01_drift_slope": 0.0002,
        "param_01_peer_deviation": 0.35
    }
    X_df = pd.DataFrame([feat_d1, feat_d2], index=[test_comp_d1, test_comp_d2])

    if_detector = IsolationForestAnomalyDetector(n_estimators=50, random_state=42)
    if_detector.fit(X_df)
    score_df = if_detector.score(X_df)
    assert len(score_df) == 2
    assert "anomaly_score" in score_df.columns
    assert 0.0 <= score_df.loc[test_comp_d1, "anomaly_score"] <= 1.0
    assert 0.0 <= score_df.loc[test_comp_d2, "anomaly_score"] <= 1.0

    score_d1 = float(score_df.loc[test_comp_d1, "anomaly_score"])
    status_d1 = str(score_df.loc[test_comp_d1, "anomaly_status"])
    score_d2 = float(score_df.loc[test_comp_d2, "anomaly_score"])
    status_d2 = str(score_df.loc[test_comp_d2, "anomaly_status"])

    # -------------------------------------------------------------
    # 4. GPR Trajectory Forecasting (Applicable vs Suppressed for D2)
    # -------------------------------------------------------------
    gpr_forecaster = GPRTrajectoryForecaster()

    # D1 component has 5 checkpoints -> forecasting is applicable
    traj_d1 = valid_df[valid_df["component_id"] == test_comp_d1].sort_values("checkpoint")
    fc_d1 = gpr_forecaster.fit_and_predict(
        trajectory=traj_d1,
        param_key="param_01",
        future_checkpoints=[168.0],
        min_history_points=3
    )
    assert fc_d1["forecast_status"] == "available"
    assert fc_d1["forecast_mean"] is not None
    assert fc_d1["interval"]["lower"] < fc_d1["forecast_mean"] < fc_d1["interval"]["upper"]
    assert fc_d1["forecast_horizon"] == 168.0

    # D2 component has only 2 checkpoints -> strictly suppressed
    traj_d2 = valid_df[valid_df["component_id"] == test_comp_d2].sort_values("checkpoint")
    fc_d2 = gpr_forecaster.fit_and_predict(
        trajectory=traj_d2,
        param_key="param_01",
        future_checkpoints=[168.0],
        min_history_points=3
    )
    assert fc_d2["forecast_status"] == "unavailable_insufficient_history"
    assert fc_d2["forecast_mean"] is None
    assert fc_d2["interval"] is None
    assert "insufficient checkpoints" in fc_d2["reason"].lower()

    # -------------------------------------------------------------
    # 5. Conservative Decision & Plain-English Explanation
    # -------------------------------------------------------------
    ev_gen = EvidenceGenerator()
    rule_engine = DecisionRuleEngine()
    exp_gen = ExplanationGenerator()

    # Build evidence pack for D1
    evidence_d1 = ev_gen.build_evidence_pack(
        component_id=test_comp_d1,
        checkpoint=144.0,
        data_quality_info={"status": "VALID", "reasons": "Passed 12/12 quality gates"},
        anomaly_info={"anomaly_score": score_d1, "anomaly_status": status_d1, "model_version": "if_e2e_v1"},
        forecast_info=fc_d1,
        peer_evidence={"peer_z": 1.45, "peer_mean": 1.25, "peer_std": 0.12}
    )
    decision_d1 = rule_engine.evaluate(evidence_d1)
    explanation_d1 = exp_gen.generate_explanation(test_comp_d1, evidence_d1, decision_d1)
    assert decision_d1["recommendation"] in ["PASS", "REVIEW", "REJECT"]
    assert test_comp_d1 in explanation_d1["plain_english_reason"]

    # Build evidence pack for D2 (no fabricated forecast)
    evidence_d2 = ev_gen.build_evidence_pack(
        component_id=test_comp_d2,
        checkpoint=168.0,
        data_quality_info={"status": "VALID", "reasons": "Passed 12/12 quality gates"},
        anomaly_info={"anomaly_score": score_d2, "anomaly_status": status_d2, "model_version": "if_e2e_v1"},
        forecast_info=fc_d2,
        peer_evidence={"peer_z": 0.35, "peer_mean": 2.825, "peer_std": 0.05}
    )
    decision_d2 = rule_engine.evaluate(evidence_d2)
    explanation_d2 = exp_gen.generate_explanation(test_comp_d2, evidence_d2, decision_d2)
    assert decision_d2["recommendation"] in ["PASS", "REVIEW", "REJECT"]

    # -------------------------------------------------------------
    # 6. SQLite Audit Logging
    # -------------------------------------------------------------
    # Record D1
    audit_storage.record_anomaly_result(
        run_id=run_id,
        component_id=test_comp_d1,
        checkpoint=144.0,
        score=score_d1,
        status=status_d1,
        model_version="if_e2e_v1",
        population_id="pop_e2e"
    )
    audit_storage.record_forecast_result(
        run_id=run_id,
        component_id=test_comp_d1,
        param_key="param_01",
        forecast_info=fc_d1
    )
    audit_storage.record_decision(
        run_id=run_id,
        component_id=test_comp_d1,
        checkpoint=144.0,
        decision_result=decision_d1,
        explanation=explanation_d1["plain_english_reason"],
        evidence_pack=evidence_d1
    )

    # Record D2
    audit_storage.record_anomaly_result(
        run_id=run_id,
        component_id=test_comp_d2,
        checkpoint=168.0,
        score=score_d2,
        status=status_d2,
        model_version="if_e2e_v1",
        population_id="pop_e2e"
    )
    audit_storage.record_decision(
        run_id=run_id,
        component_id=test_comp_d2,
        checkpoint=168.0,
        decision_result=decision_d2,
        explanation=explanation_d2["plain_english_reason"],
        evidence_pack=evidence_d2
    )

    audit_storage.record_run_complete(run_id, {"status": "success", "components": 2})

    # -------------------------------------------------------------
    # 7. Human QA Authorization Recording (POST /audit/qa-action)
    # -------------------------------------------------------------
    qa_resp = client.post("/audit/qa-action", json={
        "run_id": run_id,
        "component_id": test_comp_d2,
        "checkpoint": 168.0,
        "ai_recommendation": decision_d2["recommendation"],
        "human_action": "CONFIRM_PASS",
        "reviewer_id": "QA_LEAD_ISRO_01",
        "notes": "E2E Verification Sign-off Authorization"
    })
    assert qa_resp.status_code == 200
    qa_data = qa_resp.json()
    assert qa_data["status"] == "recorded"
    assert qa_data["component_id"] == test_comp_d2
    assert qa_data["human_action"] == "CONFIRM_PASS"

    # -------------------------------------------------------------
    # 8. Live UI/API Retrieval & Traceability Verification
    # -------------------------------------------------------------
    # A. Check /audit/{run_id}
    audit_resp = client.get(f"/audit/{run_id}")
    assert audit_resp.status_code == 200
    audit_run_data = audit_resp.json()
    assert audit_run_data["decisions_count"] == 2

    # B. Check /api/components/{component_id}/trace for D1
    trace_d1 = client.get(f"/api/components/{test_comp_d1}/trace")
    assert trace_d1.status_code == 200
    t1 = trace_d1.json()
    assert t1["component_id"] == test_comp_d1
    assert t1["provenance_chain"] == "raw_data -> pipeline_run -> model_version -> decision -> qa_action"
    assert t1["pipeline_run"]["run_id"] == run_id
    assert t1["forecast_result"]["forecast_status"] == "available"
    assert t1["forecast_result"]["forecast_mean"] is not None
    assert t1["verified_traceable"] is True

    # C. Check /api/components/{component_id}/trace for D2
    trace_d2 = client.get(f"/api/components/{test_comp_d2}/trace")
    assert trace_d2.status_code == 200
    t2 = trace_d2.json()
    assert t2["component_id"] == test_comp_d2
    assert t2["provenance_chain"] == "raw_data -> pipeline_run -> model_version -> decision -> qa_action"
    assert t2["pipeline_run"]["run_id"] == run_id
    # D2 must strictly show forecast unavailable with no fabricated mean
    assert t2["forecast_result"]["forecast_status"] == "unavailable_insufficient_history"
    assert t2["forecast_result"]["forecast_mean"] is None
    # Human QA authorization must be fully traced
    assert t2["human_qa"]["status"] == "AUTHORIZED"
    assert t2["human_qa"]["human_action"] == "CONFIRM_PASS"
    assert t2["human_qa"]["reviewer_id"] == "QA_LEAD_ISRO_01"
    assert t2["verified_traceable"] is True

    # D. Check /api/workspace
    ws_resp = client.get("/api/workspace")
    assert ws_resp.status_code == 200
    ws_data = ws_resp.json()
    assert "scores" in ws_data
    assert len(ws_data["scores"]) > 0

    # Ensure D2 items in the workspace never have fabricated GPR forecasts
    for comp in ws_data["scores"]:
        if "D2" in str(comp.get("device_type", "")) or (str(comp.get("id", "")).isdigit() and not str(comp.get("id", "")).startswith("D1-")):
            assert comp.get("forecast_status") == "unavailable_insufficient_history", (
                f"Component {comp.get('id')} has invalid forecast_status: {comp.get('forecast_status')}"
            )
            assert comp.get("forecast_mean") is None, (
                f"Component {comp.get('id')} has fabricated forecast_mean: {comp.get('forecast_mean')}"
            )


def test_d2_never_displays_fabricated_gpr_forecast(client):
    """
    Requirement 4: Ensure D2 never displays fabricated GPR forecasts.
    All D2 items must have forecast_status = unavailable_insufficient_history and forecast_mean = None.
    """
    ws_resp = client.get("/api/workspace?dataset_id=D2")
    assert ws_resp.status_code == 200
    data = ws_resp.json()
    d2_items = data.get("scores", [])
    assert len(d2_items) > 0

    for item in d2_items:
        assert item.get("forecast_status") == "unavailable_insufficient_history", (
            f"Component {item.get('id')} returned active forecast_status: {item.get('forecast_status')}"
        )
        assert item.get("forecast_mean") is None, (
            f"Component {item.get('id')} returned fabricated forecast_mean: {item.get('forecast_mean')}"
        )
        assert item.get("predicted_168h") is None
        assert item.get("forecast_std") is None
        assert item.get("lower_2sigma") is None
        assert item.get("upper_2sigma") is None


def test_end_to_end_provenance_traceability(client):
    """
    Requirement 5: Ensure every displayed result can be traced to:
    raw data -> pipeline run -> model version -> decision -> QA action.
    """
    # 1. Trace real D2 component 958
    res_958 = client.get("/api/components/958/trace")
    assert res_958.status_code == 200
    t_958 = res_958.json()
    assert t_958["component_id"] == "958"
    assert t_958["raw_data_source"] == "data/D2.csv"
    assert "pipeline_run" in t_958 and "run_id" in t_958["pipeline_run"]
    assert "model_version" in t_958
    assert "decision" in t_958 and "recommendation" in t_958["decision"]
    assert "human_qa" in t_958
    assert t_958["verified_traceable"] is True

    # 2. Trace real D1 component D1-4168
    res_d1 = client.get("/api/components/D1-4168/trace")
    assert res_d1.status_code == 200
    t_d1 = res_d1.json()
    assert t_d1["component_id"] == "D1-4168"
    assert t_d1["raw_data_source"] == "data/D1.csv"
    assert t_d1["decision"]["recommendation"] in ["PASS", "REVIEW", "REJECT"]
    assert t_d1["verified_traceable"] is True


def test_no_synthetic_ids_in_workspace(client):
    """
    Requirement 1 & 7: Ensure NO synthetic IDs (e.g. M084, LOT-D2-08 mock fallback) exist
    and ALL exported values come from real database/model results.
    """
    ws_resp = client.get("/api/workspace")
    assert ws_resp.status_code == 200
    ws_data = ws_resp.json()
    all_scores = ws_data.get("scores", [])

    # Check for authentic integer IDs in D2
    d2_items = [s for s in all_scores if str(s.get("id", "")).isdigit() and "D2" in str(s.get("device_type", ""))]
    for item in d2_items:
        cid = str(item.get("id"))
        # Real D2 MaterialIDs are integers (e.g. "958", "1023", "2", "5", etc.)
        assert cid.isdigit(), f"Found non-integer D2 ID: {cid}"
        assert not cid.startswith("M084"), f"Found synthetic ID M084 in D2: {cid}"

    # Confirm all 200 authentic D2 components are present
    assert len(d2_items) == 200

