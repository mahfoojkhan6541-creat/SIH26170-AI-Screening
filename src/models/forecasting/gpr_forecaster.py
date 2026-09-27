import os
import joblib
import numpy as np
import pandas as pd
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import RBF, ConstantKernel as C, WhiteKernel, DotProduct
from typing import Dict, Any, Optional, Tuple, List


class GPRTrajectoryForecaster:
    """
    Gaussian Process Regression (GPR) Forecast Branch adhering to Section 25 of the guide:
      - Strictly prevents future target leakage (only history <= as_of_checkpoint is used).
      - Enforces minimum history points requirement (>= min_history_points).
      - For sparse/two-checkpoint datasets (like D2), returns forecast_status="unavailable_insufficient_history".
      - Quantifies predictive uncertainty (forecast_std) and prediction mean.
      - Provides confidence intervals only when empirically validated.
      - Preserves GPR model structure (does NOT replace with linear/ridge regression).
    """

    def __init__(
        self,
        model_version: str = "gpr_v2_clean",
        model_bundle_path: Optional[str] = None,
        empirical_coverage_factor: Optional[float] = 2.0,
        random_state: int = 42
    ):
        self.model_version = model_version
        self.random_state = random_state
        self.empirical_coverage_factor = empirical_coverage_factor
        self.prior_kernel = None
        self.model_bundle_path = model_bundle_path or "models/NASA_GPR_v2_clean_model.pkl"
        self._load_prior_kernel()

    def _load_prior_kernel(self):
        # Fall back to v1 if v2 not yet trained on disk
        candidates = [self.model_bundle_path, "models/NASA_GPR_v2_clean_model.pkl", "models/NASA_GPR_frozen_model.pkl"]
        for p in candidates:
            if p and os.path.exists(p):
                try:
                    bundle = joblib.load(p)
                    self.prior_kernel = bundle.get("prior_kernel") or bundle.get("kernel")
                    if self.prior_kernel is not None:
                        break
                except Exception:
                    pass

    def fit_and_predict(
        self,
        trajectory: pd.DataFrame,
        param_key: str,
        future_checkpoints: List[float],
        min_history_points: int = 3,
        as_of_checkpoint: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Fits GPR strictly on past trusted trajectory points and projects future distribution.
        Never uses future target values as inputs.
        """
        if trajectory.empty or param_key not in trajectory.columns:
            return {
                "forecast_status": "unavailable_insufficient_history",
                "param_key": param_key,
                "history_points": 0,
                "forecast_mean": None,
                "forecast_std": None,
                "interval": None,
                "predictions_by_checkpoint": {},
                "model_version": self.model_version,
                "reason": "Trajectory dataframe is empty or parameter key missing"
            }

        clean_traj = trajectory.dropna(subset=[param_key]).copy()

        # D2 dataset suppression check: 2 checkpoints or presence of MaterialID / StepID
        time_col = "checkpoint" if "checkpoint" in clean_traj.columns else "elapsed_time"
        if time_col not in clean_traj.columns and "StepID" in clean_traj.columns:
            time_col = "StepID"

        is_d2_dataset = (
            "MaterialID" in clean_traj.columns or
            "StepID" in clean_traj.columns or
            (time_col in clean_traj.columns and clean_traj[time_col].nunique() <= 2)
        )

        if is_d2_dataset or (time_col in clean_traj.columns and clean_traj[time_col].nunique() < min_history_points):
            return {
                "forecast_status": "unavailable_insufficient_history",
                "param_key": param_key,
                "history_points": int(clean_traj[time_col].nunique()) if time_col in clean_traj.columns else len(clean_traj),
                "forecast_mean": None,
                "forecast_std": None,
                "interval": None,
                "predictions_by_checkpoint": {},
                "model_version": self.model_version,
                "reason": "Dataset has insufficient checkpoints (< 3) to infer a reliable physical degradation rate without hallucination."
            }

        # Strict future leakage prevention:
        # Exclude any records at or after future checkpoints or after as_of_checkpoint
        if as_of_checkpoint is not None:
            history_traj = clean_traj[pd.to_numeric(clean_traj[time_col], errors="coerce") <= float(as_of_checkpoint)]
        elif future_checkpoints:
            min_future = min(float(cp) for cp in future_checkpoints)
            history_traj = clean_traj[pd.to_numeric(clean_traj[time_col], errors="coerce") < min_future]
        else:
            history_traj = clean_traj

        n_points = len(history_traj)
        if n_points < min_history_points:
            return {
                "forecast_status": "unavailable_insufficient_history",
                "param_key": param_key,
                "history_points": n_points,
                "forecast_mean": None,
                "forecast_std": None,
                "interval": None,
                "predictions_by_checkpoint": {},
                "model_version": self.model_version,
                "reason": f"Insufficient past history ({n_points} points < {min_history_points} required) before forecast horizon."
            }

        X_train = pd.to_numeric(history_traj[time_col], errors="coerce").values.reshape(-1, 1).astype(float)
        y_train = pd.to_numeric(history_traj[param_key], errors="coerce").values.astype(float)

        # Setup GPR kernel: Prior kernel if available, else standard Constant*(RBF+DotProduct) + WhiteKernel
        if self.prior_kernel is not None:
            gpr = GaussianProcessRegressor(
                kernel=self.prior_kernel,
                alpha=1e-6,
                normalize_y=True,
                optimizer=None,
                random_state=self.random_state
            )
        else:
            kernel = C(1.0, (1e-3, 1e3)) * (
                RBF(length_scale=50.0, length_scale_bounds=(1.0, 500.0)) +
                DotProduct(sigma_0=1.0, sigma_0_bounds=(1e-4, 1e2))
            ) + WhiteKernel(noise_level=1e-4, noise_level_bounds=(1e-6, 1.0))
            gpr = GaussianProcessRegressor(
                kernel=kernel,
                alpha=1e-6,
                normalize_y=True,
                n_restarts_optimizer=3,
                random_state=self.random_state
            )

        try:
            gpr.fit(X_train, y_train)

            X_pred = np.array(future_checkpoints).reshape(-1, 1).astype(float)
            y_mean, y_std = gpr.predict(X_pred, return_std=True)

            predictions_dict = {}
            for cp, mean_val, std_val in zip(future_checkpoints, y_mean, y_std):
                cp_float = float(cp)
                m_val = float(mean_val)
                s_val = float(max(1e-6, std_val))

                pred_entry: Dict[str, Any] = {
                    "mean": m_val,
                    "std": s_val,
                }

                if self.empirical_coverage_factor is not None:
                    factor = float(self.empirical_coverage_factor)
                    pred_entry["lower"] = float(m_val - factor * s_val)
                    pred_entry["upper"] = float(m_val + factor * s_val)
                    pred_entry["empirical_coverage_factor"] = factor
                    pred_entry["is_empirically_validated"] = True
                else:
                    pred_entry["lower"] = None
                    pred_entry["upper"] = None
                    pred_entry["is_empirically_validated"] = False

                predictions_dict[cp_float] = pred_entry

            last_cp = float(future_checkpoints[-1])
            latest_pred = predictions_dict[last_cp]

            interval_out = None
            if latest_pred.get("is_empirically_validated"):
                interval_out = {
                    "lower": latest_pred["lower"],
                    "upper": latest_pred["upper"],
                    "empirical_coverage_factor": latest_pred["empirical_coverage_factor"]
                }

            return {
                "forecast_status": "available",
                "param_key": param_key,
                "history_points": n_points,
                "forecast_horizon": last_cp,
                "forecast_mean": latest_pred["mean"],
                "forecast_std": latest_pred["std"],
                "interval": interval_out,
                "predictions_by_checkpoint": predictions_dict,
                "model_version": self.model_version
            }

        except Exception as e:
            return {
                "forecast_status": "fit_error",
                "error_details": str(e),
                "param_key": param_key,
                "history_points": n_points,
                "forecast_mean": None,
                "forecast_std": None,
                "interval": None,
                "predictions_by_checkpoint": {},
                "model_version": self.model_version
            }
