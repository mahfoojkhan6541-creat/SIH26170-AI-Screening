"""
NASA Power Semiconductor Degradation — GPR v2 Clean Forecasting & Physical-Device Evaluation
=============================================================================================
Implementation conforming to Phase 3 requirements:
  1. Authentic physical-device grouping (Device_2, Device_3, Device_4, Device_5).
  2. No paired-device leakage across train/test splits.
  3. No future target leakage (conditioning uses only early history <= 24.0h).
  4. Preprocessing and hyperparameter prior fitted strictly on training physical devices.
  5. Empirical validation of uncertainty bounds and predictive coverage.
  6. Non-destructive versioning: saves to models/NASA_GPR_v2_clean_model.pkl.
"""

import os
import sys
import json
import joblib
import datetime

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

import numpy as np
import pandas as pd
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import RBF, ConstantKernel as C, WhiteKernel, DotProduct


def train_and_evaluate_nasa_gpr_v2():
    print("=" * 80)
    print("   NASA DEGRADATION DATASET — CLEAN GPR v2 PHYSICAL-DEVICE TRAINING & EVALUATION")
    print("=" * 80)

    canonical_path = "data/canonical/NASA_degradation_canonical.csv"
    if not os.path.exists(canonical_path):
        from src.ingestion.nasa_adapter import extract_and_save_nasa_data
        extract_and_save_nasa_data()

    df = pd.read_csv(canonical_path)
    physical_devices = sorted(df["component_id"].unique())
    print(f"\n[1] Physical Devices Verified: {physical_devices}")
    print(f"    Total canonical records: {len(df)} across {len(physical_devices)} physical hardware units")

    param_target = "param_01"  # Collector-Emitter Current (A)
    early_checkpoints = [0.0, 12.0, 24.0]
    future_checkpoints = [48.0, 72.0, 96.0, 120.0, 144.0, 168.0]

    # -------------------------------------------------------------
    # Step 1: Leave-One-Physical-Device-Out Cross-Validation (LOPD-CV)
    # -------------------------------------------------------------
    print("\n[2] Executing Leave-One-Physical-Device-Out Cross-Validation (LOPD-CV)...")
    lopd_records = []

    for test_dev in physical_devices:
        train_devs = [d for d in physical_devices if d != test_dev]
        train_df = df[df["component_id"].isin(train_devs)]
        test_df = df[df["component_id"] == test_dev]

        # Fit population prior ONLY on early history (cp <= 24h) of training devices
        train_early = train_df[train_df["checkpoint"].isin(early_checkpoints)]
        X_train_pop = train_early["checkpoint"].values.reshape(-1, 1).astype(float)
        y_train_pop = train_early[param_target].values.astype(float)

        kernel = C(1.0, (1e-3, 1e3)) * (
            RBF(length_scale=50.0, length_scale_bounds=(1.0, 500.0)) +
            DotProduct(sigma_0=1.0, sigma_0_bounds=(1e-4, 1e2))
        ) + WhiteKernel(noise_level=1e-4, noise_level_bounds=(1e-6, 1.0))

        fold_prior = GaussianProcessRegressor(
            kernel=kernel,
            alpha=1e-6,
            normalize_y=True,
            n_restarts_optimizer=3,
            random_state=42
        )
        fold_prior.fit(X_train_pop, y_train_pop)

        # Condition test GPR using learned prior kernel and ONLY test early history
        test_early = test_df[test_df["checkpoint"].isin(early_checkpoints)]
        test_future = test_df[test_df["checkpoint"].isin(future_checkpoints)]

        fold_test_gpr = GaussianProcessRegressor(
            kernel=fold_prior.kernel_,
            alpha=1e-6,
            normalize_y=True,
            optimizer=None
        )
        fold_test_gpr.fit(
            test_early["checkpoint"].values.reshape(-1, 1).astype(float),
            test_early[param_target].values.astype(float)
        )

        preds_future, stds_future = fold_test_gpr.predict(
            test_future["checkpoint"].values.reshape(-1, 1).astype(float),
            return_std=True
        )
        actuals_future = test_future[param_target].values.astype(float)

        mae_all = float(np.mean(np.abs(preds_future - actuals_future)))
        rmse_all = float(np.sqrt(np.mean((preds_future - actuals_future) ** 2)))

        # 168h horizon specific metrics
        pred_168, std_168 = fold_test_gpr.predict([[168.0]], return_std=True)
        actual_168 = float(test_df[test_df["checkpoint"] == 168.0][param_target].values[0])
        mae_168 = abs(float(pred_168[0]) - actual_168)

        # 2-sigma coverage
        lower_bounds = preds_future - 2.0 * stds_future
        upper_bounds = preds_future + 2.0 * stds_future
        covered_points = int(np.sum((actuals_future >= lower_bounds) & (actuals_future <= upper_bounds)))
        coverage_pct = float(covered_points / len(actuals_future))

        lopd_records.append({
            "held_out_device": test_dev,
            "train_devices": train_devs,
            "actual_168h": actual_168,
            "pred_168h": float(pred_168[0]),
            "std_168h": float(std_168[0]),
            "mae_168h": mae_168,
            "mae_all_future": mae_all,
            "rmse_all_future": rmse_all,
            "covered_points": covered_points,
            "total_points": len(actuals_future),
            "coverage_2sigma": coverage_pct
        })
        print(f"  Fold [{test_dev}]: Actual 168h={actual_168:.5f} A | Pred 168h={pred_168[0]:.5f} ± {2*std_168[0]:.5f} A | MAE_168h={mae_168:.5f} A | Coverage={coverage_pct*100:.1f}%")

    lopd_df = pd.DataFrame(lopd_records)
    mean_mae_168 = float(lopd_df["mae_168h"].mean())
    mean_mae_future = float(lopd_df["mae_all_future"].mean())
    mean_coverage = float(lopd_df["coverage_2sigma"].mean())

    print("\n[3] LOPD-CV Overall Performance:")
    print(f"    Mean MAE at 168h Horizon: {mean_mae_168:.5f} A")
    print(f"    Mean MAE across all Future Points: {mean_mae_future:.5f} A")
    print(f"    Mean 2-sigma Predictive Uncertainty Coverage: {mean_coverage * 100:.1f}%")

    # -------------------------------------------------------------
    # Step 2: Final Model Training on Primary Split
    # Train: Device_2, Device_3, Device_5 | Held-Out Test: Device_4
    # -------------------------------------------------------------
    train_devices_primary = ["Device_2", "Device_3", "Device_5"]
    held_out_test_device = "Device_4"

    print(f"\n[4] Training Production GPR v2 Model Bundle...")
    print(f"    Train Physical Devices: {train_devices_primary}")
    print(f"    Held-Out Test Device:   {held_out_test_device}")

    train_df = df[df["component_id"].isin(train_devices_primary)]
    train_early = train_df[train_df["checkpoint"].isin(early_checkpoints)]
    X_train_final = train_early["checkpoint"].values.reshape(-1, 1).astype(float)
    y_train_final = train_early[param_target].values.astype(float)

    kernel = C(1.0, (1e-3, 1e3)) * (
        RBF(length_scale=50.0, length_scale_bounds=(1.0, 500.0)) +
        DotProduct(sigma_0=1.0, sigma_0_bounds=(1e-4, 1e2))
    ) + WhiteKernel(noise_level=1e-4, noise_level_bounds=(1e-6, 1.0))

    final_gpr_prior = GaussianProcessRegressor(
        kernel=kernel,
        alpha=1e-6,
        normalize_y=True,
        n_restarts_optimizer=5,
        random_state=42
    )
    final_gpr_prior.fit(X_train_final, y_train_final)
    print(f"    Fitted Prior Kernel: {final_gpr_prior.kernel_}")

    # Evaluate on held-out test device (Device_4)
    test_df = df[df["component_id"] == held_out_test_device]
    test_early = test_df[test_df["checkpoint"].isin(early_checkpoints)]
    test_future = test_df[test_df["checkpoint"].isin(future_checkpoints)]

    gpr_test = GaussianProcessRegressor(
        kernel=final_gpr_prior.kernel_,
        alpha=1e-6,
        normalize_y=True,
        optimizer=None
    )
    gpr_test.fit(
        test_early["checkpoint"].values.reshape(-1, 1).astype(float),
        test_early[param_target].values.astype(float)
    )

    preds_d4, stds_d4 = gpr_test.predict(
        test_future["checkpoint"].values.reshape(-1, 1).astype(float),
        return_std=True
    )
    actuals_d4 = test_future[param_target].values.astype(float)
    actual_168_d4 = float(test_df[test_df["checkpoint"] == 168.0][param_target].values[0])
    pred_168_d4 = float(preds_d4[-1])
    std_168_d4 = float(stds_d4[-1])
    mae_168_d4 = abs(pred_168_d4 - actual_168_d4)
    mae_all_d4 = float(np.mean(np.abs(preds_d4 - actuals_d4)))
    coverage_d4 = float(np.sum((actuals_d4 >= preds_d4 - 2*stds_d4) & (actuals_d4 <= preds_d4 + 2*stds_d4)) / len(actuals_d4))

    print(f"\n[5] Held-Out Test Device [{held_out_test_device}] Results:")
    print(f"    Actual Value at 168h:    {actual_168_d4:.5f} A")
    print(f"    Predicted Value at 168h: {pred_168_d4:.5f} ± {2*std_168_d4:.5f} A")
    print(f"    Held-Out MAE at 168h:    {mae_168_d4:.5f} A (Relative Error: {(mae_168_d4/actual_168_d4)*100:.2f}%)")
    print(f"    Mean MAE across 48h..168h: {mae_all_d4:.5f} A")
    print(f"    2-sigma Uncertainty Coverage: {coverage_d4 * 100:.1f}%")

    # -------------------------------------------------------------
    # Step 3: Save Non-Destructive Clean Model Bundle
    # -------------------------------------------------------------
    os.makedirs("models", exist_ok=True)
    v2_bundle_path = "models/NASA_GPR_v2_clean_model.pkl"

    model_bundle = {
        "model_version": "gpr_v2_clean",
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "prior_kernel": final_gpr_prior.kernel_,
        "gpr_model": final_gpr_prior,
        "param_target": param_target,
        "early_history_checkpoints": early_checkpoints,
        "forecast_horizon_hours": 168.0,
        "training_physical_devices": train_devices_primary,
        "held_out_test_device": held_out_test_device,
        "metrics_held_out": {
            "actual_168h": actual_168_d4,
            "pred_168h": pred_168_d4,
            "std_168h": std_168_d4,
            "mae_168h": mae_168_d4,
            "mae_all_future": mae_all_d4,
            "coverage_2sigma": coverage_d4
        },
        "metrics_lopd_cv": {
            "mean_mae_168h": mean_mae_168,
            "mean_mae_future": mean_mae_future,
            "mean_coverage_2sigma": mean_coverage,
            "fold_results": lopd_records
        },
        "physical_device_mapping": {
            "Device2": "Device_2",
            "Device2b": "Device_2",
            "Device3": "Device_3",
            "Device3b": "Device_3",
            "Device4": "Device_4",
            "Device4b": "Device_4",
            "Device5": "Device_5"
        }
    }

    joblib.dump(model_bundle, v2_bundle_path)
    print(f"\n[6] Saved new GPR v2 model bundle to: {v2_bundle_path}")
    print(f"    (Preserved original frozen model: models/NASA_GPR_frozen_model.pkl)")

    # -------------------------------------------------------------
    # Step 4: Update Model Registry (configs/model_registry.json)
    # -------------------------------------------------------------
    registry_path = "configs/model_registry.json"
    registry_data = {}
    if os.path.exists(registry_path):
        with open(registry_path, "r", encoding="utf-8") as f:
            registry_data = json.load(f)

    registry_data["NASA_GPR_v2"] = {
        "dataset_name": "NASA PCoE Power Semiconductor Thermal Aging (Physical Device Clean)",
        "model_type": "GaussianProcessRegressor",
        "model_path": v2_bundle_path,
        "param_target": param_target,
        "early_history_hours": 24.0,
        "forecast_horizon_hours": 168.0,
        "status": "frozen",
        "version": "v2_physical_device_clean",
        "physical_devices_used": ["Device_2", "Device_3", "Device_4", "Device_5"],
        "training_devices": train_devices_primary,
        "held_out_test_device": held_out_test_device,
        "metrics": {
            "held_out_mae_168h": round(mae_168_d4, 6),
            "held_out_relative_error_pct": round((mae_168_d4 / actual_168_d4) * 100, 2),
            "held_out_coverage_2sigma": coverage_d4,
            "lopd_cv_mean_mae_168h": round(mean_mae_168, 6),
            "lopd_cv_mean_coverage_2sigma": round(mean_coverage, 4)
        },
        "trained_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
    }

    with open(registry_path, "w", encoding="utf-8") as f:
        json.dump(registry_data, f, indent=2)

    print(f"[7] Updated model registry: {registry_path} with NASA_GPR_v2 metadata.\n")
    return model_bundle


if __name__ == "__main__":
    train_and_evaluate_nasa_gpr_v2()
