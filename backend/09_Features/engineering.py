import pandas as pd
import numpy as np
from typing import Dict, Any, List, Tuple
from .baseline import BaselineFeatureExtractor
from .drift import DriftFeatureExtractor
from .peer_relative import PeerRelativeFeatureExtractor
from backend.stage_08_reference_population.population_selector import PopulationSelector
from backend.stage_06_confounders.time_align import TimeAligner


class FeatureEngineeringEngine:
    """Orchestrates behavior representation, peer-relative deviations, and metadata separation."""

    def __init__(self, feature_version: str = "feat_v1"):
        self.feature_version = feature_version
        self.pop_selector = PopulationSelector()

    def build_feature_bundle_for_component(
        self,
        canonical_df: pd.DataFrame,
        component_id: str,
        checkpoint: Any,
        param_keys: List[str]
    ) -> Dict[str, Any]:
        """
        Builds complete feature bundle for one component at a specific checkpoint.
        Strictly enforces the no-future-information rule.
        """
        # 1. Select reference population peers as of this checkpoint (Target Excluded!)
        pop_info = self.pop_selector.select_reference_population(
            canonical_df=canonical_df,
            target_component_id=component_id,
            checkpoint=checkpoint,
            as_of_checkpoint=checkpoint
        )
        peers_df = pop_info.get("members_df", pd.DataFrame())

        numerical_features: Dict[str, float] = {}
        explanation_evidence: Dict[str, Any] = {}
        feature_status: Dict[str, str] = {}

        for p in param_keys:
            # Trajectory up to current checkpoint
            traj = TimeAligner.get_component_trajectory(
                canonical_df,
                component_id=component_id,
                param_key=p,
                as_of_checkpoint=checkpoint
            )

            # Baseline features
            b_feat = BaselineFeatureExtractor.extract(traj, p)
            numerical_features[f"{p}_current"] = b_feat[f"{p}_current"]
            numerical_features[f"{p}_delta_baseline"] = b_feat[f"{p}_delta_from_baseline"]
            explanation_evidence[f"{p}_baseline"] = b_feat[f"{p}_baseline"]

            # Drift features
            d_feat = DriftFeatureExtractor.extract(traj, p)
            numerical_features[f"{p}_drift_slope"] = d_feat[f"{p}_drift_slope"]
            numerical_features[f"{p}_trajectory_std"] = d_feat[f"{p}_trajectory_std"]
            if not np.isnan(d_feat[f"{p}_curvature"]):
                numerical_features[f"{p}_curvature"] = d_feat[f"{p}_curvature"]
            feature_status[f"{p}_curvature"] = d_feat.get("curvature_status", "unavailable_insufficient_points")

            # Peer-relative features
            current_val = b_feat[f"{p}_current"]
            pr_feat = PeerRelativeFeatureExtractor.extract(current_val, peers_df, p)
            numerical_features[f"{p}_peer_zscore"] = pr_feat[f"{p}_peer_zscore"]
            explanation_evidence[f"{p}_peer_mean"] = pr_feat[f"{p}_peer_mean"]
            explanation_evidence[f"{p}_peer_std"] = pr_feat[f"{p}_peer_std"]
            explanation_evidence[f"{p}_peer_diff"] = pr_feat[f"{p}_peer_diff"]

        # Category B: Context / Grouping Metadata
        context_metadata = {
            "component_id": str(component_id),
            "checkpoint": checkpoint,
            "population_id": pop_info.get("population_id", "none"),
            "population_level": pop_info.get("level", "none"),
            "peer_count": pop_info.get("peer_count", 0)
        }

        # Category D: Evaluation Metadata (never passed to unsupervised models)
        eval_metadata = {}
        comp_rows = canonical_df[(canonical_df["component_id"] == str(component_id)) & (canonical_df["checkpoint"] == checkpoint)]
        if not comp_rows.empty:
            first_row = comp_rows.iloc[0]
            if "evaluation_label" in first_row:
                eval_metadata["evaluation_label"] = first_row["evaluation_label"]
            if "split_assignment" in first_row:
                eval_metadata["split_assignment"] = first_row["split_assignment"]

        # Category E: Audit Metadata
        audit_metadata = {
            "feature_version": self.feature_version,
            "feature_status": feature_status
        }

        return {
            "numerical_features": numerical_features,
            "context_metadata": context_metadata,
            "explanation_evidence": explanation_evidence,
            "evaluation_metadata": eval_metadata,
            "audit_metadata": audit_metadata
        }

    def extract_feature_matrix_batch(
        self,
        canonical_df: pd.DataFrame,
        param_keys: List[str],
        checkpoint: Any
    ) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """
        Batch feature extractor for all components at a specific checkpoint.
        Returns:
            - X_df: Clean numeric feature DataFrame (Model Inputs Category A)
            - meta_df: Context and explanation metadata (Category B & C)
            - eval_df: Evaluation labels and split assignments (Category D)
        """
        cp_df = canonical_df[canonical_df["checkpoint"] == checkpoint]
        unique_components = cp_df["component_id"].unique()

        x_list = []
        meta_list = []
        eval_list = []

        for comp_id in unique_components:
            bundle = self.build_feature_bundle_for_component(canonical_df, comp_id, checkpoint, param_keys)
            
            # Numeric features
            num_dict = bundle["numerical_features"].copy()
            num_dict["component_id"] = comp_id
            x_list.append(num_dict)

            # Metadata
            meta_dict = {**bundle["context_metadata"], **bundle["explanation_evidence"]}
            meta_list.append(meta_dict)

            # Evaluation
            eval_dict = {"component_id": comp_id, **bundle["evaluation_metadata"]}
            eval_list.append(eval_dict)

        X_df = pd.DataFrame(x_list).set_index("component_id")
        meta_df = pd.DataFrame(meta_list).set_index("component_id")
        eval_df = pd.DataFrame(eval_list).set_index("component_id")

        # Impute any remaining NaNs with 0.0 for robust model consumption
        X_df = X_df.fillna(0.0)

        return X_df, meta_df, eval_df

    def extract_registered_features(
        self,
        df: pd.DataFrame,
        expected_features: List[str]
    ) -> pd.DataFrame:
        """
        Extracts high-integrity validated features (level, drift, rolling std, spikes,
        stabilization, trajectory change, peer deviations, acceleration if required)
        strictly matching a pre-trained frozen model's expected feature schema.
        """
        df_copy = df.copy()
        id_col = "MaterialID" if "MaterialID" in df_copy.columns else "component_id"
        time_col = "duration_ms" if "duration_ms" in df_copy.columns else "elapsed_time"
        step_col = "StepID" if "StepID" in df_copy.columns else "checkpoint"

        if id_col not in df_copy.columns:
            raise ValueError(f"Required identifier column '{id_col}' not found in dataframe.")

        df_copy["_source_order"] = np.arange(len(df_copy))
        sort_cols = [c for c in [id_col, time_col, "_source_order"] if c in df_copy.columns]
        df_copy = df_copy.sort_values(sort_cols).reset_index(drop=True)

        raw_features = [
            c for c in df_copy.columns
            if c.startswith("feature_") and not any(
                c.endswith(s) for s in [
                    "_delta", "_slope", "_rolling_std", "_spike",
                    "_acceleration", "_stabilization", "_trajectory_change",
                    "_peer_deviation"
                ]
            )
        ]

        feats = {}
        # 1. Level & Delta
        for f in raw_features:
            feats[f] = df_copy[f].values
            prev = df_copy.groupby(id_col)[f].shift(1).values
            delta = df_copy[f].values - prev
            feats[f"{f}_delta"] = delta

        # 2. Slope / Drift
        dt_safe = np.ones(len(df_copy), dtype=float)
        if time_col in df_copy.columns:
            prev_time = df_copy.groupby(id_col)[time_col].shift(1).values
            dt = df_copy[time_col].values - prev_time
            dt_safe = np.where(dt > 0, dt, np.nan)

        for f in raw_features:
            slope = feats[f"{f}_delta"] / dt_safe
            feats[f"{f}_slope"] = slope

        # 3. Acceleration
        for f in raw_features:
            prev_slope = pd.Series(feats[f"{f}_slope"]).groupby(df_copy[id_col]).shift(1).values
            feats[f"{f}_acceleration"] = (feats[f"{f}_slope"] - prev_slope) / dt_safe

        # 4. Rolling std & spikes
        for f in raw_features:
            rolling_std = df_copy.groupby(id_col)[f].transform(lambda x: x.rolling(3, min_periods=1).std()).values
            feats[f"{f}_rolling_std"] = rolling_std
            mean_3 = df_copy.groupby(id_col)[f].transform(lambda x: x.rolling(3, min_periods=1).mean()).values
            std_3 = df_copy.groupby(id_col)[f].transform(lambda x: x.rolling(3, min_periods=1).std()).replace(0.0, 1e-6).values
            feats[f"{f}_spike"] = np.abs(df_copy[f].values - mean_3) / std_3

        # 5. Stabilization
        for f in raw_features:
            first_val = df_copy.groupby(id_col)[f].transform("first").values
            feats[f"{f}_stabilization"] = np.abs(df_copy[f].values - first_val)

        # 6. Trajectory change
        for f in raw_features:
            prev_slope = pd.Series(feats[f"{f}_slope"]).groupby(df_copy[id_col]).shift(1).values
            feats[f"{f}_trajectory_change"] = np.abs(feats[f"{f}_slope"] - prev_slope)

        # 7. Raw summary
        if raw_features:
            raw_matrix = df_copy[raw_features].values
            feats["measurement_mean"] = np.nanmean(raw_matrix, axis=1)
            feats["measurement_std"] = np.nanstd(raw_matrix, axis=1)

        # 8. Peer deviations
        for f in raw_features:
            if step_col in df_copy.columns:
                peer_mean = df_copy.groupby(step_col)[f].transform("mean").values
                peer_std = df_copy.groupby(step_col)[f].transform("std").replace(0.0, 1e-6).values
                feats[f"{f}_peer_deviation"] = (df_copy[f].values - peer_mean) / peer_std
            else:
                feats[f"{f}_peer_deviation"] = np.zeros(len(df_copy))

        feats_df = pd.DataFrame(feats)
        feats_df[id_col] = df_copy[id_col].values

        # Aggregate to component/material decision level (latest state)
        latest_feats = feats_df.groupby(id_col).last()

        # Reindex to exact expected features
        avail = [c for c in expected_features if c in latest_feats.columns]
        result_df = latest_feats[avail].apply(pd.to_numeric, errors="coerce").fillna(0.0)
        return result_df

