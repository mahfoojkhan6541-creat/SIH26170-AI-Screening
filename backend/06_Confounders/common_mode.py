import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional, Union, Tuple


class CommonModeDetector:
    """
    Context-aware common-mode confounder detection using peer group trajectories.
    Preserves Part Type, Part Number, Lot, and test context boundaries.
    Never pools across incompatible physical part types.

    Detects synchronized step shifts where a large fraction (>= threshold_pct, default 60%)
    of comparable peers undergo the same directional shift at the same checkpoint.

    Returns deterministic evidence dictionary:
      - affected_peer_count: int
      - total_peer_count: int
      - percentage_affected: float
      - affected_checkpoint: Any
      - common_mode_status: str ("DETECTED" | "NOMINAL")
      - suspected_confounder: str
      - shift_direction: str ("POSITIVE" | "NEGATIVE" | "NONE")
      - shift_magnitude: float
      - common_mode_detected: bool
      - status: str ("detected" | "nominal")
    """

    CONTEXT_COLUMNS = [
        "part_type",
        "part_number",
        "lot_id",
        "lot",
        "batch_id",
        "test_condition",
        "chamber_id",
        "tester_id"
    ]

    TIME_COLUMNS = [
        "checkpoint",
        "elapsed_time",
        "StepID",
        "step_id",
        "cycle",
        "raw_cycle"
    ]

    EXCLUDED_PARAM_COLUMNS = set(CONTEXT_COLUMNS + TIME_COLUMNS + [
        "component_id",
        "MaterialID",
        "is_test",
        "target",
        "quality_status",
        "quality_reasons",
        "anomaly_score",
        "anomaly_status",
        "unit",
        "units"
    ])

    def __init__(self, threshold_pct: float = 60.0, min_peers: int = 3, noise_multiplier: float = 1.5):
        """
        Args:
            threshold_pct: Percentage of peers (>= threshold_pct) required to declare common-mode shift.
            min_peers: Minimum peer cohort size required to evaluate common-mode drift.
            noise_multiplier: Multiplier over baseline noise floor to deem a delta significant.
        """
        self.threshold_pct = threshold_pct
        self.min_peers = min_peers
        self.noise_multiplier = noise_multiplier

    @staticmethod
    def get_nominal_evidence(checkpoint: Any = None) -> Dict[str, Any]:
        """Returns standard deterministic nominal evidence structure."""
        return {
            "common_mode_detected": False,
            "status": "nominal",
            "common_mode_status": "NOMINAL",
            "affected_peer_count": 0,
            "total_peer_count": 0,
            "percentage_affected": 0.0,
            "affected_checkpoint": checkpoint,
            "suspected_confounder": "None",
            "shift_direction": "NONE",
            "shift_magnitude": 0.0,
            "affected_parameter": None,
            "context_group": {}
        }

    def _resolve_time_col(self, df: pd.DataFrame) -> Optional[str]:
        for col in self.TIME_COLUMNS:
            if col in df.columns:
                return col
        return None

    def _resolve_param_keys(self, df: pd.DataFrame, param_keys: Optional[List[str]]) -> List[str]:
        if param_keys:
            return [p for p in param_keys if p in df.columns]
        # Auto-discover numeric parameters
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        return [c for c in numeric_cols if c not in self.EXCLUDED_PARAM_COLUMNS]

    def _resolve_id_col(self, df: pd.DataFrame) -> str:
        if "component_id" in df.columns:
            return "component_id"
        if "MaterialID" in df.columns:
            return "MaterialID"
        return "component_id"

    def get_context_for_target(self, df: pd.DataFrame, target_id: Any) -> Dict[str, Any]:
        """Extracts available context metadata for target component."""
        id_col = self._resolve_id_col(df)
        if id_col not in df.columns:
            return {}
        target_rows = df[df[id_col].astype(str) == str(target_id)]
        if target_rows.empty:
            return {}
        context = {}
        row = target_rows.iloc[0]
        for col in self.CONTEXT_COLUMNS:
            if col in df.columns and pd.notnull(row[col]):
                context[col] = row[col]
        return context

    def filter_comparable_peers(
        self,
        df: pd.DataFrame,
        target_id: Optional[Any],
        target_context: Optional[Dict[str, Any]] = None
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Filters dataframe to comparable peer units preserving Part Type / Part Number / Lot / test context.
        Strictly prevents pooling across different physical part types.
        Excludes the target component itself.
        """
        id_col = self._resolve_id_col(df)
        if target_context is None and target_id is not None:
            target_context = self.get_context_for_target(df, target_id)
        else:
            target_context = target_context or {}

        # Base filter: exclude target component if specified
        if target_id is not None and id_col in df.columns:
            peer_df = df[df[id_col].astype(str) != str(target_id)].copy()
        else:
            peer_df = df.copy()

        applied_context = {}

        # 1. STRICT PART TYPE MATCH: Never pool across different part types
        if "part_type" in target_context and "part_type" in peer_df.columns:
            peer_df = peer_df[peer_df["part_type"] == target_context["part_type"]]
            applied_context["part_type"] = target_context["part_type"]

        # 2. Match test conditions / environment if present
        for env_col in ["test_condition", "chamber_id", "tester_id"]:
            if env_col in target_context and env_col in peer_df.columns:
                cond_peers = peer_df[peer_df[env_col] == target_context[env_col]]
                # Retain condition constraint if peer population remains viable
                if cond_peers[id_col].nunique() >= self.min_peers:
                    peer_df = cond_peers
                    applied_context[env_col] = target_context[env_col]

        # 3. Match Part Number and Lot if available
        if "part_number" in target_context and "part_number" in peer_df.columns:
            pn_peers = peer_df[peer_df["part_number"] == target_context["part_number"]]
            if pn_peers[id_col].nunique() >= self.min_peers:
                peer_df = pn_peers
                applied_context["part_number"] = target_context["part_number"]

        lot_col = next((c for c in ["lot_id", "lot", "batch_id"] if c in target_context and c in peer_df.columns), None)
        if lot_col:
            lot_peers = peer_df[peer_df[lot_col] == target_context[lot_col]]
            if lot_peers[id_col].nunique() >= self.min_peers:
                peer_df = lot_peers
                applied_context[lot_col] = target_context[lot_col]

        return peer_df, applied_context

    def detect_for_component(
        self,
        canonical_df: pd.DataFrame,
        target_component_id: Any,
        checkpoint: Optional[Any] = None,
        param_keys: Optional[List[str]] = None,
        context_override: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Executes deterministic context-aware common-mode detection for a target component at a checkpoint.
        """
        if canonical_df.empty:
            return self.get_nominal_evidence(checkpoint)

        time_col = self._resolve_time_col(canonical_df)
        id_col = self._resolve_id_col(canonical_df)
        params = self._resolve_param_keys(canonical_df, param_keys)

        if not time_col or not params:
            return self.get_nominal_evidence(checkpoint)

        # Context extraction and peer filtering
        target_ctx = context_override or self.get_context_for_target(canonical_df, target_component_id)
        peer_df, applied_ctx = self.filter_comparable_peers(
            canonical_df,
            target_id=target_component_id,
            target_context=target_ctx
        )

        unique_peers = peer_df[id_col].dropna().unique().tolist()
        total_peer_count = len(unique_peers)

        if total_peer_count < self.min_peers:
            evidence = self.get_nominal_evidence(checkpoint)
            evidence["total_peer_count"] = total_peer_count
            evidence["context_group"] = applied_ctx
            return evidence

        # Resolve checkpoint sequence
        try:
            available_cps = sorted(canonical_df[time_col].dropna().unique(), key=float)
        except Exception:
            available_cps = sorted(canonical_df[time_col].dropna().unique())

        if checkpoint is None:
            eval_cp = available_cps[-1] if available_cps else None
        else:
            eval_cp = checkpoint

        if eval_cp is None or eval_cp not in available_cps:
            evidence = self.get_nominal_evidence(eval_cp)
            evidence["total_peer_count"] = total_peer_count
            evidence["context_group"] = applied_ctx
            return evidence

        cp_idx = available_cps.index(eval_cp)
        if cp_idx == 0:
            # Baseline checkpoint - no preceding checkpoint to detect temporal shift from
            evidence = self.get_nominal_evidence(eval_cp)
            evidence["total_peer_count"] = total_peer_count
            evidence["context_group"] = applied_ctx
            return evidence

        prev_cp = available_cps[cp_idx - 1]

        # Evaluate synchronized shift across parameters
        best_detection: Optional[Dict[str, Any]] = None
        max_affected_ratio = 0.0

        # Pre-filter peer records to only the two evaluation checkpoints to avoid repeated table scans
        cp_subset = peer_df[peer_df[time_col].isin([prev_cp, eval_cp])]
        if cp_subset.empty:
            evidence = self.get_nominal_evidence(eval_cp)
            evidence["total_peer_count"] = total_peer_count
            evidence["context_group"] = applied_ctx
            return evidence

        curr_records = cp_subset[cp_subset[time_col] == eval_cp].drop_duplicates(subset=[id_col]).set_index(id_col)
        prev_records = cp_subset[cp_subset[time_col] == prev_cp].drop_duplicates(subset=[id_col]).set_index(id_col)
        common_peers = curr_records.index.intersection(prev_records.index)

        if len(common_peers) == 0:
            evidence = self.get_nominal_evidence(eval_cp)
            evidence["total_peer_count"] = total_peer_count
            evidence["context_group"] = applied_ctx
            return evidence

        curr_aligned = curr_records.loc[common_peers]
        prev_aligned = prev_records.loc[common_peers]

        for p in params:
            c_series = pd.to_numeric(curr_aligned[p], errors="coerce")
            p_series = pd.to_numeric(prev_aligned[p], errors="coerce")
            valid_mask = c_series.notnull() & p_series.notnull()

            if not valid_mask.any():
                continue

            c_vals = c_series[valid_mask].to_numpy(dtype=float)
            p_vals = p_series[valid_mask].to_numpy(dtype=float)
            shifts = c_vals - p_vals
            baseline_vals = p_vals

            n_shifts = len(shifts)
            if n_shifts == 0:
                continue

            # Baseline noise floor
            if len(baseline_vals) > 1:
                base_std = float(np.std(baseline_vals))
            else:
                base_std = 0.0
            noise_floor = max(1e-6, base_std * 0.15)
            sig_threshold = noise_floor * self.noise_multiplier

            # Count directional shifts exceeding noise threshold
            pos_shifts = shifts[shifts > sig_threshold]
            neg_shifts = shifts[shifts < -sig_threshold]

            pos_count = len(pos_shifts)
            neg_count = len(neg_shifts)

            if pos_count >= neg_count:
                lead_count = pos_count
                direction = "POSITIVE"
                avg_magnitude = float(np.mean(pos_shifts)) if pos_count > 0 else 0.0
            else:
                lead_count = neg_count
                direction = "NEGATIVE"
                avg_magnitude = float(abs(np.mean(neg_shifts))) if neg_count > 0 else 0.0

            ratio = lead_count / max(n_shifts, 1)
            pct = round(ratio * 100.0, 1)

            is_detected = (pct >= self.threshold_pct) and (n_shifts >= self.min_peers)

            detection_candidate = {
                "common_mode_detected": bool(is_detected),
                "status": "detected" if is_detected else "nominal",
                "common_mode_status": "DETECTED" if is_detected else "NOMINAL",
                "affected_peer_count": int(lead_count),
                "total_peer_count": int(n_shifts),
                "percentage_affected": float(pct),
                "affected_checkpoint": eval_cp,
                "suspected_confounder": (
                    "Thermal Chamber Step / Test Fixture Common-Mode Shift"
                    if is_detected else "None"
                ),
                "shift_direction": direction if is_detected else "NONE",
                "shift_magnitude": float(round(avg_magnitude, 6)),
                "affected_parameter": p if is_detected else None,
                "context_group": applied_ctx
            }

            if is_detected:
                # Return immediately or keep highest magnitude detection
                if best_detection is None or pct > best_detection["percentage_affected"]:
                    best_detection = detection_candidate
            else:
                if best_detection is None or (not best_detection["common_mode_detected"] and ratio >= max_affected_ratio):
                    max_affected_ratio = ratio
                    best_detection = detection_candidate

        if best_detection is not None:
            return best_detection

        evidence = self.get_nominal_evidence(eval_cp)
        evidence["total_peer_count"] = total_peer_count
        evidence["context_group"] = applied_ctx
        return evidence

    def detect_population_wide(
        self,
        canonical_df: pd.DataFrame,
        checkpoint: Optional[Any] = None,
        param_keys: Optional[List[str]] = None
    ) -> Dict[str, Dict[str, Any]]:
        """
        Runs common-mode detection across all distinct component context groups in the dataset.
        Returns a map from component_id to its deterministic confounder evidence.
        """
        id_col = self._resolve_id_col(canonical_df)
        if id_col not in canonical_df.columns:
            return {}

        results = {}
        unique_components = canonical_df[id_col].dropna().unique()
        for cid in unique_components:
            results[cid] = self.detect_for_component(
                canonical_df=canonical_df,
                target_component_id=cid,
                checkpoint=checkpoint,
                param_keys=param_keys
            )
        return results
