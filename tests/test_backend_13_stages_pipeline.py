"""
End-to-End Verification of the 13-Stage ISRO Data Pipeline Architecture
========================================================================
Tests that all 13 stages in backend/ can be imported, instantiated,
and executed sequentially from Stage 01 through Stage 13.
"""
import pytest
import pandas as pd
import numpy as np

import backend
from backend.stage_01_input import AUTHENTIC_DATASETS
from backend.stage_02_intake import IntakeAdapterFactory, DatasetRegistry
from backend.stage_03_profiling import AutoProfiler, CompatibilityChecker
from backend.stage_04_context_mapping import MappingLoader, UnitConverter
from backend.stage_05_data_quality import DataQualityValidator, QuarantineManager
from backend.stage_06_confounders import CommonModeDetector, TimeAligner
from backend.stage_07_canonical import CanonicalTransformer
from backend.stage_08_reference_population import PopulationPolicy, PopulationSelector
from backend.stage_09_features import FeatureEngineeringEngine
from backend.stage_10_models import IsolationForestAnomalyDetector, GPRTrajectoryForecaster
from backend.stage_11_evidence import EvidenceGenerator, MultiParameterCorrelationDetector
from backend.stage_12_decision_explanation import DecisionRuleEngine, ExplanationGenerator
from backend.stage_13_qa_audit_api import AuditStorage, ProgressiveStateManager, app
from fastapi.testclient import TestClient


def test_stage_01_to_13_modules_exist_and_importable():
    """Confirms all 13 numbered stage packages are accessible via backend."""
    assert hasattr(backend, "stage_01_input")
    assert hasattr(backend, "stage_02_intake")
    assert hasattr(backend, "stage_03_profiling")
    assert hasattr(backend, "stage_04_context_mapping")
    assert hasattr(backend, "stage_05_data_quality")
    assert hasattr(backend, "stage_06_confounders")
    assert hasattr(backend, "stage_07_canonical")
    assert hasattr(backend, "stage_08_reference_population")
    assert hasattr(backend, "stage_09_features")
    assert hasattr(backend, "stage_10_models")
    assert hasattr(backend, "stage_11_evidence")
    assert hasattr(backend, "stage_12_decision_explanation")
    assert hasattr(backend, "stage_13_qa_audit_api")


def test_stage_clean_aliases_exist():
    """Confirms friendly semantic aliases exist in backend."""
    assert hasattr(backend, "intake")
    assert hasattr(backend, "profiling")
    assert hasattr(backend, "context_mapping")
    assert hasattr(backend, "data_quality")
    assert hasattr(backend, "confounders")
    assert hasattr(backend, "canonical")
    assert hasattr(backend, "reference_population")
    assert hasattr(backend, "features")
    assert hasattr(backend, "models")
    assert hasattr(backend, "evidence")
    assert hasattr(backend, "decision_explanation")
    assert hasattr(backend, "qa_audit_api")


def test_sequential_data_flow_01_to_13():
    """
    Executes a complete sequential pass through all 13 stages:
    01_Input -> 02_Intake -> 03_Profiling -> 04_Context_Mapping -> 
    05_Data_Quality -> 06_Confounders -> 07_Canonical -> 
    08_Reference_Population -> 09_Features -> 10_Models -> 
    11_Evidence -> 12_Decision_Explanation -> 13_QA_Audit_API
    """
    # Stage 01: Input Data
    d1_path = AUTHENTIC_DATASETS["D1"]
    assert d1_path is not None

    # Stage 02: Dataset Intake & Registration
    adapter = IntakeAdapterFactory.get_adapter(d1_path)
    raw_df = adapter.load(d1_path)
    assert len(raw_df) > 0
    assert isinstance(raw_df, pd.DataFrame)

    registry = DatasetRegistry()
    assert len(registry.registered_datasets) > 0

    # Stage 03: Profiling & Compatibility
    profiler = AutoProfiler()
    profile = profiler.profile(raw_df, "D1_Verification")
    checker = CompatibilityChecker()
    compat = checker.assess_compatibility(profile)
    assert compat["branches"]["anomaly_branch"] == "compatible"

    # Stage 04: Context Mapping & Unit Conversion
    mapping_loader = MappingLoader()
    d1_mapping = mapping_loader.load_mapping("d1_mapping")
    assert "identity_fields" in d1_mapping
    unit_conv = UnitConverter()
    assert unit_conv is not None

    # Stage 05: Data Quality Gate (12-Check Decomposition)
    validator = DataQualityValidator()
    # Canonicalize subset for validation test
    transformer = CanonicalTransformer(mapping_loader=mapping_loader, unit_converter=unit_conv)
    canonical_df, _ = transformer.transform(raw_df.head(50), d1_mapping, "D1")
    param_keys = [p["parameter_key"] for p in d1_mapping["parameter_fields"]]
    valid_df, quarantined_df, val_summary = validator.validate(canonical_df, param_keys=param_keys[:2])
    assert "valid_records" in val_summary
    assert len(valid_df) > 0
    quarantine = QuarantineManager()
    assert quarantine is not None

    # Stage 06: Confounder Handling
    cm_detector = CommonModeDetector()
    assert cm_detector is not None
    cps = TimeAligner.get_ordered_checkpoints(canonical_df)
    assert len(cps) > 0

    # Stage 07: Canonical Representation
    assert "component_id" in canonical_df.columns
    assert "checkpoint" in canonical_df.columns
    assert "param_01" in canonical_df.columns

    # Stage 08: Reference Population & Grouping
    pop_selector = PopulationSelector()
    target_comp = canonical_df["component_id"].iloc[0]
    first_cp = cps[0]
    pop_info = pop_selector.select_reference_population(
        canonical_df=canonical_df,
        target_component_id=target_comp,
        checkpoint=first_cp
    )
    assert "status" in pop_info
    if not pop_info["members_df"].empty:
        assert target_comp not in pop_info["members_df"]["component_id"].values

    # Stage 09: Feature Engineering
    engine = FeatureEngineeringEngine()
    features = engine.build_feature_bundle_for_component(
        canonical_df=canonical_df,
        component_id=target_comp,
        checkpoint=first_cp,
        param_keys=["param_01"]
    )
    assert "numerical_features" in features

    # Stage 10: AI Model Branches
    if_detector = IsolationForestAnomalyDetector(n_estimators=30)
    feat_df = pd.DataFrame([features["numerical_features"]])
    if_detector.fit(feat_df)
    score_df = if_detector.score(feat_df)
    assert "anomaly_score" in score_df.columns
    forecaster = GPRTrajectoryForecaster()
    assert forecaster is not None

    # Stage 11: Evidence Evaluation
    evidence_pack = EvidenceGenerator.build_evidence_pack(
        component_id=target_comp,
        checkpoint=first_cp,
        data_quality_info={"status": "VALID", "reasons": "Nominal"},
        anomaly_info={"anomaly_score": float(score_df["anomaly_score"].iloc[0]), "anomaly_status": "normal"},
        forecast_info=None,
        peer_evidence={"peer_zscore": 0.2}
    )
    assert evidence_pack["component_id"] == str(target_comp)

    # Stage 12: Decision Rules & Explainable AI
    rule_engine = DecisionRuleEngine()
    decision = rule_engine.evaluate(evidence_pack)
    assert decision["recommendation"] in ["PASS", "REVIEW", "REJECT", "RETEST"]
    explanation = ExplanationGenerator.generate_explanation(target_comp, evidence_pack, decision)
    assert "plain_english_narrative" in explanation
    assert len(explanation["plain_english_narrative"]) > 20

    # Stage 13: QA Audit & Serving API
    audit = AuditStorage()
    state = ProgressiveStateManager()
    comp_state = state.get_or_create_state(target_comp)
    assert comp_state["component_id"] == str(target_comp)

    client = TestClient(app)
    health_res = client.get("/health")
    assert health_res.status_code == 200
    assert health_res.json()["status"] == "healthy"
