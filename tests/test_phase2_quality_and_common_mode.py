import pytest
import numpy as np
import pandas as pd
from src.validation.validator import DataQualityValidator
from src.validation.quarantine import QuarantineManager
from src.grouping.common_mode import CommonModeDetector
from src.evidence.generator import EvidenceGenerator
from src.decision.rules import DecisionRuleEngine


# =====================================================================
# Fixtures for Data Quality Gate
# =====================================================================

@pytest.fixture
def clean_canonical_df():
    """A clean, valid canonical dataset with multiple components and checkpoints."""
    records = []
    for c_idx in range(1, 6):
        cid = f"DEV_{c_idx:02d}"
        for cp in [0.0, 12.0, 24.0, 48.0]:
            records.append({
                "component_id": cid,
                "part_type": "IGBT_Power_MOSFET",
                "part_number": "IRG4BC30KD",
                "lot_id": "LOT_ALPHA",
                "checkpoint": cp,
                "elapsed_time": cp,
                "unit": "V",
                "param_01": 2.5 + (0.01 * cp) + np.random.normal(0, 0.005),
                "param_02": 100.0 + (0.05 * cp) + np.random.normal(0, 0.01)
            })
    return pd.DataFrame(records)


# =====================================================================
# Tests: All 12 Data Quality Gate Checks
# =====================================================================

class TestDataQualityGateAll12Cases:

    def test_clean_data_passes_all_12_checks(self, clean_canonical_df):
        validator = DataQualityValidator()
        valid_df, quarantined_df, summary = validator.validate(
            clean_canonical_df, param_keys=["param_01", "param_02"]
        )

        assert len(quarantined_df) == 0
        assert len(valid_df) == len(clean_canonical_df)
        assert summary["quarantined_records"] == 0
        assert summary["blocked_records"] == 0

        # All 12 cases must report PASS
        for i in range(1, 13):
            case_key = f"case_{i:02d}"
            assert summary["all_checks_status"][case_key] == "PASS"

    def test_case_01_missing_reading(self, clean_canonical_df):
        df = clean_canonical_df.copy()
        # Set all measurement parameters to NaN for row 0
        df.loc[0, "param_01"] = np.nan
        df.loc[0, "param_02"] = np.nan

        validator = DataQualityValidator()
        valid_df, quarantined_df, summary = validator.validate(df, ["param_01", "param_02"])

        assert summary["all_checks_status"]["case_01_missing_reading"] == "QUARANTINE"
        assert len(quarantined_df) == 1
        assert "case_01_missing_reading" in [e["case_id"] for e in summary["events_detected"]]
        assert any(e["action"] == "QUARANTINE" for e in summary["events_detected"])

    def test_case_02_partial_missingness(self, clean_canonical_df):
        df = clean_canonical_df.copy()
        # Set only param_01 to NaN (param_02 remains valid)
        df.loc[0, "param_01"] = np.nan

        validator = DataQualityValidator()
        valid_df, quarantined_df, summary = validator.validate(df, ["param_01", "param_02"])

        assert summary["all_checks_status"]["case_02_partial_missingness"] == "WARNING"
        # Partial missingness is a WARNING, so record remains in valid_df (not quarantined)
        assert len(quarantined_df) == 0
        assert len(valid_df) == len(df)

    def test_case_03_sensor_error_inf(self, clean_canonical_df):
        df = clean_canonical_df.copy()
        # Insert Infinite sensor error
        df.loc[2, "param_01"] = np.inf

        validator = DataQualityValidator()
        valid_df, quarantined_df, summary = validator.validate(df, ["param_01", "param_02"])

        assert summary["all_checks_status"]["case_03_sensor_error"] == "BLOCK"
        assert len(quarantined_df) == 1
        assert quarantined_df.iloc[0]["quality_status"] == "BLOCK"

    def test_case_04_duplicate_reading(self, clean_canonical_df):
        df = clean_canonical_df.copy()
        # Duplicate row 0
        dup_row = df.iloc[[0]].copy()
        df = pd.concat([df, dup_row], ignore_index=True)

        validator = DataQualityValidator()
        valid_df, quarantined_df, summary = validator.validate(df, ["param_01", "param_02"])

        assert summary["all_checks_status"]["case_04_duplicate_reading"] == "WARNING"
        assert any(e["case_id"] == "case_04_duplicate_reading" for e in summary["events_detected"])

    def test_case_05_invalid_timestamp(self, clean_canonical_df):
        df = clean_canonical_df.copy()
        # Negative elapsed time
        df.loc[1, "elapsed_time"] = -10.0

        validator = DataQualityValidator()
        valid_df, quarantined_df, summary = validator.validate(df, ["param_01", "param_02"])

        assert summary["all_checks_status"]["case_05_wrong_timestamp"] == "QUARANTINE"
        assert len(quarantined_df) >= 1

    def test_case_06_wrong_component_id(self, clean_canonical_df):
        df = clean_canonical_df.copy()
        # Corrupt component ID to blank/unknown
        df.loc[3, "component_id"] = "UNKNOWN"

        validator = DataQualityValidator()
        valid_df, quarantined_df, summary = validator.validate(df, ["param_01", "param_02"])

        assert summary["all_checks_status"]["case_06_wrong_component_id"] == "BLOCK"
        assert len(quarantined_df) >= 1
        assert quarantined_df.iloc[0]["quality_status"] == "BLOCK"

    def test_case_07_wrong_unit(self, clean_canonical_df):
        df = clean_canonical_df.copy()
        # Unrecognized unit
        df.loc[4, "unit"] = "invalid_alien_unit_99"

        validator = DataQualityValidator()
        valid_df, quarantined_df, summary = validator.validate(df, ["param_01", "param_02"])

        assert summary["all_checks_status"]["case_07_wrong_unit"] == "BLOCK"
        assert len(quarantined_df) >= 1

    def test_case_08_measurement_saturation(self, clean_canonical_df):
        df = clean_canonical_df.copy()
        # Extreme statistical outlier (> 6-sigma)
        df.loc[0, "param_01"] = 9999.0

        validator = DataQualityValidator()
        valid_df, quarantined_df, summary = validator.validate(df, ["param_01", "param_02"])

        assert summary["all_checks_status"]["case_08_measurement_saturation"] == "WARNING"

    def test_case_09_sensor_flatline(self, clean_canonical_df):
        df = clean_canonical_df.copy()
        # Set parameter 02 to exact zero variance across the whole dataset
        df["param_02"] = 5.000000

        validator = DataQualityValidator()
        valid_df, quarantined_df, summary = validator.validate(df, ["param_01", "param_02"])

        assert summary["all_checks_status"]["case_09_sensor_noise"] == "WARNING"
        assert any("case_09_sensor_noise" in e["case_id"] for e in summary["events_detected"])

    def test_case_10_communication_dropout(self, clean_canonical_df):
        # Create a component with normal step 12, then sudden gap to 200
        records = []
        for cp in [0.0, 12.0, 24.0, 200.0]:  # gap 176 >> 3 * 12
            records.append({
                "component_id": "DEV_DROPOUT",
                "part_type": "IGBT_Power_MOSFET",
                "checkpoint": cp,
                "elapsed_time": cp,
                "unit": "V",
                "param_01": 2.5 + (0.01 * cp)
            })
        df = pd.DataFrame(records)

        validator = DataQualityValidator()
        valid_df, quarantined_df, summary = validator.validate(df, ["param_01"])

        assert summary["all_checks_status"]["case_10_communication_failure"] == "QUARANTINE"
        assert len(quarantined_df) >= 1

    def test_case_11_out_of_order_timestamps(self, clean_canonical_df):
        records = [
            {"component_id": "DEV_REV", "checkpoint": 0.0, "elapsed_time": 0.0, "unit": "V", "param_01": 1.0},
            {"component_id": "DEV_REV", "checkpoint": 24.0, "elapsed_time": 24.0, "unit": "V", "param_01": 1.2},
            {"component_id": "DEV_REV", "checkpoint": 12.0, "elapsed_time": 12.0, "unit": "V", "param_01": 1.1},  # reversed!
        ]
        df = pd.DataFrame(records)

        validator = DataQualityValidator()
        valid_df, quarantined_df, summary = validator.validate(df, ["param_01"])

        assert summary["all_checks_status"]["case_11_out_of_order_records"] == "WARNING"

    def test_case_12_clock_mismatch(self, clean_canonical_df):
        records = [
            {"component_id": "DEV_CLOCK", "checkpoint": 12.0, "elapsed_time": 100.0, "unit": "V", "param_01": 1.0},
            {"component_id": "DEV_CLOCK", "checkpoint": 24.0, "elapsed_time": 50.0, "unit": "V", "param_01": 1.2},  # cp +12, elapsed -50!
        ]
        df = pd.DataFrame(records)

        validator = DataQualityValidator()
        valid_df, quarantined_df, summary = validator.validate(df, ["param_01"])

        assert summary["all_checks_status"]["case_12_clock_mismatch"] == "WARNING"


# =====================================================================
# Tests: Common-Mode Detection & Context Preservation
# =====================================================================

class TestCommonModeDetectionAndContextPreservation:

    def test_synchronized_common_mode_shift_detected(self):
        """When >= 60% of peers undergo a simultaneous shift, detect common mode."""
        records = []
        # 5 peers + 1 target component in LOT_A
        for cid in ["DEV_TARGET", "DEV_P1", "DEV_P2", "DEV_P3", "DEV_P4", "DEV_P5"]:
            # Baseline at cp 0
            records.append({
                "component_id": cid,
                "part_type": "IGBT_Power_MOSFET",
                "part_number": "IRG4BC30KD",
                "lot_id": "LOT_A",
                "checkpoint": 0.0,
                "param_01": 1.00 + np.random.normal(0, 0.005)
            })
            # Synchronized upward shift of +0.50 at cp 12 across all peers
            records.append({
                "component_id": cid,
                "part_type": "IGBT_Power_MOSFET",
                "part_number": "IRG4BC30KD",
                "lot_id": "LOT_A",
                "checkpoint": 12.0,
                "param_01": 1.50 + np.random.normal(0, 0.005)
            })
        df = pd.DataFrame(records)

        detector = CommonModeDetector(threshold_pct=60.0, min_peers=3)
        evidence = detector.detect_for_component(
            canonical_df=df,
            target_component_id="DEV_TARGET",
            checkpoint=12.0,
            param_keys=["param_01"]
        )

        assert evidence["common_mode_detected"] is True
        assert evidence["common_mode_status"] == "DETECTED"
        assert evidence["affected_peer_count"] == 5  # All 5 peers shifted
        assert evidence["total_peer_count"] == 5
        assert evidence["percentage_affected"] == 100.0
        assert evidence["affected_checkpoint"] == 12.0
        assert evidence["shift_direction"] == "POSITIVE"
        assert evidence["shift_magnitude"] > 0.4
        assert "Thermal Chamber" in evidence["suspected_confounder"]

    def test_isolated_anomaly_not_flagged_as_common_mode(self):
        """When only 1 peer out of 5 drifts, common mode must NOT be detected."""
        records = []
        for cid in ["DEV_TARGET", "DEV_P1", "DEV_P2", "DEV_P3", "DEV_P4", "DEV_P5"]:
            # Baseline at cp 0
            records.append({
                "component_id": cid,
                "part_type": "IGBT_Power_MOSFET",
                "part_number": "IRG4BC30KD",
                "lot_id": "LOT_A",
                "checkpoint": 0.0,
                "param_01": 1.00
            })
            # At cp 12, only DEV_P1 drifts (+0.60), others stay stable (1.00)
            val = 1.60 if cid == "DEV_P1" else 1.00
            records.append({
                "component_id": cid,
                "part_type": "IGBT_Power_MOSFET",
                "part_number": "IRG4BC30KD",
                "lot_id": "LOT_A",
                "checkpoint": 12.0,
                "param_01": val
            })
        df = pd.DataFrame(records)

        detector = CommonModeDetector(threshold_pct=60.0, min_peers=3)
        evidence = detector.detect_for_component(
            canonical_df=df,
            target_component_id="DEV_TARGET",
            checkpoint=12.0,
            param_keys=["param_01"]
        )

        assert evidence["common_mode_detected"] is False
        assert evidence["common_mode_status"] == "NOMINAL"
        assert evidence["affected_peer_count"] <= 1
        assert evidence["percentage_affected"] <= 20.0
        assert evidence["shift_direction"] == "NONE"

    def test_baseline_checkpoint_is_always_nominal(self):
        """At checkpoint 0 (baseline), no prior checkpoint exists, so common mode must be NOMINAL."""
        records = []
        for cid in ["DEV_TARGET", "DEV_P1", "DEV_P2", "DEV_P3"]:
            records.append({
                "component_id": cid,
                "part_type": "IGBT_Power_MOSFET",
                "part_number": "IRG4BC30KD",
                "lot_id": "LOT_A",
                "checkpoint": 0.0,
                "param_01": 2.50
            })
        df = pd.DataFrame(records)

        detector = CommonModeDetector()
        evidence = detector.detect_for_component(df, "DEV_TARGET", checkpoint=0.0, param_keys=["param_01"])

        assert evidence["common_mode_detected"] is False
        assert evidence["common_mode_status"] == "NOMINAL"
        assert evidence["affected_peer_count"] == 0
        assert evidence["percentage_affected"] == 0.0

    def test_context_preservation_no_cross_type_pooling(self):
        """
        Crucial requirement: Preserve Part Type.
        Units of Type B (GaN HEMT) experiencing a common-mode shift must NEVER contaminate
        or be pooled into the peer group of Type A (IGBT Power MOSFET).
        """
        records = []

        # Population A: IGBT_Power_MOSFET (completely stable, NO shift)
        for cid in ["IGBT_01", "IGBT_02", "IGBT_03", "IGBT_04"]:
            records.append({
                "component_id": cid,
                "part_type": "IGBT_Power_MOSFET",
                "part_number": "IRG4BC30KD",
                "lot_id": "LOT_A",
                "checkpoint": 0.0,
                "param_01": 1.00
            })
            records.append({
                "component_id": cid,
                "part_type": "IGBT_Power_MOSFET",
                "part_number": "IRG4BC30KD",
                "lot_id": "LOT_A",
                "checkpoint": 12.0,
                "param_01": 1.00  # perfectly stable
            })

        # Population B: Discrete_GaN_HEMT (experiences massive chamber step shift +2.0)
        for cid in ["HEMT_01", "HEMT_02", "HEMT_03", "HEMT_04"]:
            records.append({
                "component_id": cid,
                "part_type": "Discrete_GaN_HEMT",
                "part_number": "EPC2001C",
                "lot_id": "LOT_B",
                "checkpoint": 0.0,
                "param_01": 10.00
            })
            records.append({
                "component_id": cid,
                "part_type": "Discrete_GaN_HEMT",
                "part_number": "EPC2001C",
                "lot_id": "LOT_B",
                "checkpoint": 12.0,
                "param_01": 12.00  # +2.0 common shift!
            })

        df = pd.DataFrame(records)
        detector = CommonModeDetector(threshold_pct=60.0, min_peers=3)

        # 1. Evaluate IGBT_01: Its peer cohort must contain ONLY other IGBT units
        igbt_evidence = detector.detect_for_component(
            canonical_df=df,
            target_component_id="IGBT_01",
            checkpoint=12.0,
            param_keys=["param_01"]
        )
        assert igbt_evidence["common_mode_detected"] is False
        assert igbt_evidence["common_mode_status"] == "NOMINAL"
        assert igbt_evidence["total_peer_count"] == 3  # IGBT_02, IGBT_03, IGBT_04 (target IGBT_01 excluded)
        assert igbt_evidence["context_group"]["part_type"] == "IGBT_Power_MOSFET"

        # 2. Evaluate HEMT_01: Its peer cohort must contain ONLY other HEMT units
        hemt_evidence = detector.detect_for_component(
            canonical_df=df,
            target_component_id="HEMT_01",
            checkpoint=12.0,
            param_keys=["param_01"]
        )
        assert hemt_evidence["common_mode_detected"] is True
        assert hemt_evidence["common_mode_status"] == "DETECTED"
        assert hemt_evidence["total_peer_count"] == 3  # HEMT_02, HEMT_03, HEMT_04
        assert hemt_evidence["affected_peer_count"] == 3
        assert hemt_evidence["percentage_affected"] == 100.0
        assert hemt_evidence["shift_direction"] == "POSITIVE"
        assert hemt_evidence["context_group"]["part_type"] == "Discrete_GaN_HEMT"

    def test_evidence_pack_and_decision_rule_with_common_mode(self):
        """Verify common-mode evidence routes to REVIEW under RULE_COMMON_MODE_CONFOUNDER."""
        confounder_info = {
            "common_mode_detected": True,
            "status": "detected",
            "common_mode_status": "DETECTED",
            "affected_peer_count": 5,
            "total_peer_count": 5,
            "percentage_affected": 100.0,
            "affected_checkpoint": 24.0,
            "suspected_confounder": "Thermal Chamber Step",
            "shift_direction": "POSITIVE",
            "shift_magnitude": 0.45
        }

        # Build evidence pack
        evidence = EvidenceGenerator.build_evidence_pack(
            component_id="TEST_DEV",
            checkpoint=24.0,
            data_quality_info={"status": "VALID", "reasons": "Passed quality gate"},
            anomaly_info={"anomaly_score": 0.60, "anomaly_status": "normal", "model_version": "v1"},
            forecast_info=None,
            peer_evidence={},
            confounder_info=confounder_info
        )

        assert evidence["confounder"]["common_mode_detected"] is True
        assert evidence["confounder"]["affected_peer_count"] == 5

        # Decision rule evaluation
        engine = DecisionRuleEngine()
        decision = engine.evaluate(evidence)

        # Common-mode triggers REVIEW with RULE_COMMON_MODE_CONFOUNDER
        assert decision["recommendation"] == "REVIEW"
        assert decision["triggered_rule"] == "RULE_COMMON_MODE_CONFOUNDER"
        assert "Common-mode drift" in decision["action"]
