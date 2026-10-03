import pandas as pd
from typing import Dict, Any, Optional, Tuple, List
from .population_policy import PopulationPolicy
from .population_validator import PopulationValidator


class PopulationSelector:
    """
    Selects and validates comparable peer reference populations for a target component
    according to Section 19 of the Generalized Data Pipeline Implementation Guide.

    Features:
      - Multi-attribute context matching (Part Type, Part Number, Lot/Batch, Test Conditions)
      - Strict Target Exclusion (target component is never included in its own reference set)
      - No-Leakage Time Filtering (only past or concurrent checkpoint data is visible)
      - 4-Level Documented Fallback Hierarchy
      - Deterministic and Auditable Population IDs
      - Minimum Population Size Enforcement (>= min_size)
    """

    def __init__(self, policy: Optional[PopulationPolicy] = None, validator: Optional[PopulationValidator] = None):
        self.policy = policy or PopulationPolicy()
        self.validator = validator or PopulationValidator()

    def select_reference_population(
        self,
        canonical_df: pd.DataFrame,
        target_component_id: str,
        checkpoint: Any,
        as_of_checkpoint: Optional[Any] = None,
        context_override: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Selects reference peer components enforcing target exclusion and hierarchical fallback.
        """
        target_id_str = str(target_component_id)

        # Step 1: Time Filtering - Only use data available at or before analysis time (no leakage)
        cutoff_cp = as_of_checkpoint if as_of_checkpoint is not None else checkpoint
        if isinstance(cutoff_cp, (int, float)) and "checkpoint" in canonical_df.columns:
            try:
                time_filtered = canonical_df[canonical_df["checkpoint"].astype(float) <= float(cutoff_cp)]
            except Exception:
                time_filtered = canonical_df[canonical_df["checkpoint"] == cutoff_cp]
        elif "checkpoint" in canonical_df.columns:
            time_filtered = canonical_df[canonical_df["checkpoint"] == cutoff_cp]
        else:
            time_filtered = canonical_df.copy()

        # Step 2: Target Exclusion - Ensure target component never contaminates its own reference
        peers_candidates = time_filtered[time_filtered["component_id"].astype(str) != target_id_str]

        # Extract target component's context attributes if available in dataset
        target_rows = canonical_df[canonical_df["component_id"].astype(str) == target_id_str]
        target_context = {}
        if not target_rows.empty:
            for col in ["part_type", "part_number", "lot_id", "test_condition", "chamber_id", "tester_id"]:
                if col in target_rows.columns and pd.notnull(target_rows[col].iloc[0]):
                    target_context[col] = target_rows[col].iloc[0]

        if context_override:
            target_context.update(context_override)

        # Step 3: Iterate through hierarchical policy levels
        levels = self.policy.get_levels()
        fallback_log = []

        for level_key, level_cfg in levels.items():
            keys: List[str] = level_cfg.get("keys", ["checkpoint"])
            min_size: int = level_cfg.get("min_population_size", 5)
            level_name: str = level_cfg.get("name", level_key)

            # Match on grouping keys available in peers_candidates
            query_mask = pd.Series(True, index=peers_candidates.index)
            matched_keys = []
            unconstrained_keys = []

            for k in keys:
                if k == "checkpoint":
                    if "checkpoint" in peers_candidates.columns:
                        query_mask &= (peers_candidates["checkpoint"] == checkpoint)
                        matched_keys.append("checkpoint")
                elif k in target_context and k in peers_candidates.columns:
                    query_mask &= (peers_candidates[k] == target_context[k])
                    matched_keys.append(f"{k}={target_context[k]}")
                else:
                    unconstrained_keys.append(k)

            matched_peers = peers_candidates[query_mask]

            is_valid, val_reason = self.validator.validate_population(
                peer_df=matched_peers,
                target_component_id=target_id_str,
                checkpoint=checkpoint,
                min_size=min_size
            )

            if is_valid:
                # Construct clean, auditable population ID
                pop_id_parts = [level_key]
                if "lot_id" in target_context:
                    pop_id_parts.append(str(target_context["lot_id"]))
                if "part_number" in target_context:
                    pop_id_parts.append(str(target_context["part_number"]))
                pop_id_parts.append(f"cp{checkpoint}")
                pop_id = f"pop_{'_'.join(pop_id_parts)}"

                return {
                    "status": "VALID",
                    "population_id": pop_id,
                    "level": level_key,
                    "level_name": level_name,
                    "matched_keys": matched_keys,
                    "unconstrained_keys": unconstrained_keys,
                    "peer_count": int(matched_peers["component_id"].nunique()),
                    "total_records": int(len(matched_peers)),
                    "members_df": matched_peers,
                    "fallback_history": fallback_log,
                    "reason": f"Successfully selected reference population at {level_name} with {matched_peers['component_id'].nunique()} peers"
                }
            else:
                fallback_log.append({
                    "level": level_key,
                    "level_name": level_name,
                    "candidate_peers": int(matched_peers["component_id"].nunique()),
                    "rejection_reason": val_reason
                })

        # Step 4: Controlled non-model fallback outcome
        return {
            "status": "UNAVAILABLE",
            "population_id": "pop_unavailable_fallback",
            "level": "none",
            "level_name": "no_approved_reference",
            "matched_keys": [],
            "unconstrained_keys": [],
            "peer_count": 0,
            "total_records": 0,
            "members_df": pd.DataFrame(),
            "fallback_history": fallback_log,
            "reason": "No approved comparable peer population satisfies minimum size and quality requirements"
        }
