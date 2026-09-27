import os
import json
import pytest
import numpy as np
import pandas as pd
from src.ingestion.nasa_adapter import NasaMatAdapter
from src.models.forecasting.gpr_forecaster import GPRTrajectoryForecaster
from src.evidence.generator import EvidenceGenerator


# =====================================================================
# 1. Tests for Base / Base-b Physical Device Grouping
# =====================================================================

class TestNasaPhysicalDeviceGrouping:

    def test_base_and_base_b_mapping(self):
        """Verifies that base and base-b files map to the same physical device."""
        mapping = NasaMatAdapter.get_physical_device_mapping()

        # Device 2 & 2b must map to the same physical device
        assert mapping["Device2"] == "Device_2"
        assert mapping["Device2b"] == "Device_2"

        # Device 3 & 3b must map to the same physical device
        assert mapping["Device3"] == "Device_3"
        assert mapping["Device3b"] == "Device_3"

        # Device 4 & 4b must map to the same physical device
        assert mapping["Device4"] == "Device_4"
        assert mapping["Device4b"] == "Device_4"

        # Device 5 is a single device
        assert mapping["Device5"] == "Device_5"

    def test_canonical_dataset_physical_device_count(self):
        """Verifies that the canonical dataset contains 4 physical devices, not 7 artificial devices."""
        canonical_path = "data/canonical/NASA_degradation_canonical.csv"
        assert os.path.exists(canonical_path), "Canonical NASA dataset must exist"

        df = pd.read_csv(canonical_path)
        unique_phys_devs = df["component_id"].unique()

        # Exactly 4 physical devices
        assert len(unique_phys_devs) == 4
        assert set(unique_phys_devs) == {"Device_2", "Device_3", "Device_4", "Device_5"}

        # Each physical device must have all 9 standard checkpoints (0h..168h)
        for dev_id in unique_phys_devs:
            dev_df = df[df["component_id"] == dev_id]
            assert len(dev_df) == 9
            assert sorted(dev_df["checkpoint"].tolist()) == [0.0, 12.0, 24.0, 48.0, 72.0, 96.0, 120.0, 144.0, 168.0]


# =====================================================================
# 2. Tests for Physical-Device Leakage Prevention
# =====================================================================

class TestPhysicalDeviceLeakagePrevention:

    def test_no_paired_device_leakage_across_splits(self):
        """
        Verifies that base and base-b pairs are NEVER split across train and test.
        Any split having Device2 in train and Device2b in test is detected and flagged as a leakage violation.
        """
        mapping = NasaMatAdapter.get_physical_device_mapping()

        def is_valid_physical_split(train_files, test_files):
            train_phys = {mapping.get(f, f) for f in train_files}
            test_phys = {mapping.get(f, f) for f in test_files}
            return len(train_phys.intersection(test_phys)) == 0

        # Valid physical device split (no overlap of physical units)
        assert is_valid_physical_split(
            train_files=["Device2", "Device2b", "Device3", "Device3b", "Device5"],
            test_files=["Device4", "Device4b"]
        ) is True

        # LEAKAGE VIOLATION: Device2 in train, Device2b in test
        assert is_valid_physical_split(
            train_files=["Device2", "Device3", "Device4", "Device5"],
            test_files=["Device2b"]
        ) is False

        # LEAKAGE VIOLATION: Device3 in train, Device3b in test
        assert is_valid_physical_split(
            train_files=["Device2", "Device3", "Device4"],
            test_files=["Device3b", "Device4b"]
        ) is False


# =====================================================================
# 3. Tests for Future Target Leakage Prevention
# =====================================================================

class TestFutureLeakagePrevention:

    def test_gpr_excludes_future_target_values_from_conditioning(self):
        """
        Verifies that GPR fits ONLY on past checkpoints (<= as_of_checkpoint or < min_future).
        Future values present in the input trajectory must NEVER be used in X_train/y_train.
        """
        forecaster = GPRTrajectoryForecaster(model_version="test_v2")

        # Create full trajectory of 9 checkpoints with an obvious artificial future jump at 48h..168h
        records = []
        for cp in [0.0, 12.0, 24.0, 48.0, 72.0, 96.0, 120.0, 144.0, 168.0]:
            # At 0..24, current is 0.12. At 48..168, artificial extreme spike to 999.0
            val = 0.12 if cp <= 24.0 else 999.0
            records.append({"checkpoint": cp, "param_01": val})
        full_traj = pd.DataFrame(records)

        # Forecast future checkpoints 48..168 using as_of_checkpoint=24.0
        result = forecaster.fit_and_predict(
            trajectory=full_traj,
            param_key="param_01",
            future_checkpoints=[48.0, 72.0, 96.0, 120.0, 144.0, 168.0],
            as_of_checkpoint=24.0,
            min_history_points=3
        )

        assert result["forecast_status"] == "available"
        assert result["history_points"] == 3  # Strictly only 0h, 12h, 24h used!

        # Because future 999.0 was strictly excluded, forecast mean at 168h must be close to 0.12, NOT near 999.0
        assert result["forecast_mean"] < 1.0


# =====================================================================
# 4. Tests for Minimum History Validation & D2 Suppression
# =====================================================================

class TestInsufficientHistoryAndD2Suppression:

    def test_insufficient_history_returns_unavailable_status(self):
        """When history points < min_history_points, return unavailable_insufficient_history."""
        forecaster = GPRTrajectoryForecaster(model_version="test_v2")

        # Trajectory with only 2 checkpoints
        traj_2cp = pd.DataFrame([
            {"checkpoint": 0.0, "param_01": 0.12},
            {"checkpoint": 24.0, "param_01": 0.11}
        ])

        result = forecaster.fit_and_predict(
            trajectory=traj_2cp,
            param_key="param_01",
            future_checkpoints=[48.0, 168.0],
            min_history_points=3
        )

        assert result["forecast_status"] == "unavailable_insufficient_history"
        assert result["forecast_mean"] is None
        assert result["forecast_std"] is None
        assert result["interval"] is None

    def test_d2_dataset_strictly_suppresses_168h_forecast(self):
        """
        Dataset D2 has only 2 checkpoints (pre/post burn-in).
        Verifies that GPR refuses to generate a fake 168h forecast.
        """
        forecaster = GPRTrajectoryForecaster()

        # D2 format: MaterialID, StepID, duration_ms, feature_1..feature_20
        d2_row_1 = {"MaterialID": 958, "StepID": 1, "feature_1": 2.82, "checkpoint": 0.0}
        d2_row_2 = {"MaterialID": 958, "StepID": 2, "feature_1": 2.85, "checkpoint": 24.0}
        d2_traj = pd.DataFrame([d2_row_1, d2_row_2])

        result = forecaster.fit_and_predict(
            trajectory=d2_traj,
            param_key="feature_1",
            future_checkpoints=[168.0],
            min_history_points=3
        )

        assert result["forecast_status"] == "unavailable_insufficient_history"
        assert result["forecast_mean"] is None
        assert result["forecast_std"] is None
        assert result["interval"] is None
        assert "insufficient checkpoints" in result["reason"].lower()

    def test_evidence_pack_preserves_unavailable_insufficient_history(self):
        """EvidenceGenerator must propagate unavailable_insufficient_history status."""
        forecast_info = {
            "forecast_status": "unavailable_insufficient_history",
            "forecast_mean": None,
            "forecast_std": None,
            "interval": None
        }

        evidence = EvidenceGenerator.build_evidence_pack(
            component_id="D2_TEST_01",
            checkpoint=24.0,
            data_quality_info={"status": "VALID", "reasons": "Passed"},
            anomaly_info={"anomaly_score": 0.35, "anomaly_status": "normal"},
            forecast_info=forecast_info,
            peer_evidence={}
        )

        assert evidence["forecast"]["status"] == "unavailable_insufficient_history"
        assert evidence["forecast"]["mean"] is None
        assert evidence["forecast"]["std"] is None


# =====================================================================
# 5. Tests for Uncertainty Output & Empirical Validation
# =====================================================================

class TestUncertaintyOutputAndCalibration:

    def test_gpr_predictive_uncertainty_grows_with_horizon(self):
        """Predictive uncertainty (std) must be positive and generally grow or widen further in the future."""
        forecaster = GPRTrajectoryForecaster()

        clean_history = pd.DataFrame([
            {"checkpoint": 0.0, "param_01": 0.120},
            {"checkpoint": 12.0, "param_01": 0.115},
            {"checkpoint": 24.0, "param_01": 0.110}
        ])

        result = forecaster.fit_and_predict(
            trajectory=clean_history,
            param_key="param_01",
            future_checkpoints=[48.0, 96.0, 168.0],
            min_history_points=3
        )

        assert result["forecast_status"] == "available"
        preds = result["predictions_by_checkpoint"]

        assert 48.0 in preds
        assert 168.0 in preds

        std_48 = preds[48.0]["std"]
        std_168 = preds[168.0]["std"]

        assert std_48 > 0
        assert std_168 > 0
        # Uncertainty at 168h must be greater than or equal to near-term 48h
        assert std_168 >= std_48

    def test_empirically_validated_interval_bounds(self):
        """When empirical coverage factor is provided, lower and upper bounds must be consistent."""
        forecaster = GPRTrajectoryForecaster(empirical_coverage_factor=2.0)

        clean_history = pd.DataFrame([
            {"checkpoint": 0.0, "param_01": 0.120},
            {"checkpoint": 12.0, "param_01": 0.115},
            {"checkpoint": 24.0, "param_01": 0.110}
        ])

        result = forecaster.fit_and_predict(
            trajectory=clean_history,
            param_key="param_01",
            future_checkpoints=[168.0],
            min_history_points=3
        )

        assert result["interval"] is not None
        lower = result["interval"]["lower"]
        upper = result["interval"]["upper"]
        mean = result["forecast_mean"]
        std = result["forecast_std"]

        assert upper > lower
        assert np.isclose(lower, mean - 2.0 * std)
        assert np.isclose(upper, mean + 2.0 * std)


# =====================================================================
# 6. Tests for Model Registry and Clean V2 Preservation
# =====================================================================

class TestModelRegistryAndV2Preservation:

    def test_v2_model_bundle_exists_and_v1_preserved(self):
        """Ensures that NASA_GPR_v2 exists and NASA_GPR_frozen_model.pkl was not overwritten."""
        v1_path = "models/NASA_GPR_frozen_model.pkl"
        v2_path = "models/NASA_GPR_v2_clean_model.pkl"

        assert os.path.exists(v1_path), "Original frozen GPR model must be preserved"
        assert os.path.exists(v2_path), "Clean GPR v2 model bundle must exist"

    def test_model_registry_contains_nasa_gpr_v2_metadata(self):
        """configs/model_registry.json must contain NASA_GPR_v2 metadata."""
        registry_path = "configs/model_registry.json"
        assert os.path.exists(registry_path)

        with open(registry_path, "r", encoding="utf-8") as f:
            registry = json.load(f)

        assert "NASA_GPR_v2" in registry
        entry = registry["NASA_GPR_v2"]

        assert entry["model_path"] == "models/NASA_GPR_v2_clean_model.pkl"
        assert entry["held_out_test_device"] == "Device_4"
        assert len(entry["physical_devices_used"]) == 4
        assert "held_out_mae_168h" in entry["metrics"]
        assert "lopd_cv_mean_mae_168h" in entry["metrics"]
        assert "held_out_coverage_2sigma" in entry["metrics"]
        assert entry["metrics"]["held_out_coverage_2sigma"] == 1.0
