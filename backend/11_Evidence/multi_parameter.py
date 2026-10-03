import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple


class MultiParameterCorrelationDetector:
    """
    Detects abnormal joint behavior across parameters using strictly validated
    numerical relationships (empirical population covariance and correlation).
    Does NOT invent physical laws or assume unverified hardware properties.
    """

    def __init__(self, corr_threshold: float = 0.50, joint_z_threshold: float = 3.0, regularization: float = 1e-4):
        """
        Args:
            corr_threshold: Minimum empirical Pearson |r| to consider a parameter pair coupled.
            joint_z_threshold: Z-score divergence threshold to declare abnormal joint discordance.
            regularization: Regularization parameter added to correlation matrix diagonal for numerical stability.
        """
        self.corr_threshold = corr_threshold
        self.joint_z_threshold = joint_z_threshold
        self.regularization = regularization

    @staticmethod
    def get_nominal_evidence() -> Dict[str, Any]:
        """Returns standard nominal evidence when multi-parameter data is absent or normal."""
        return {
            "status": "NOMINAL",
            "abnormal_joint_behavior_detected": False,
            "mahalanobis_distance": 0.0,
            "multivariate_z_score": 0.0,
            "num_evaluated_parameters": 0,
            "num_correlated_pairs": 0,
            "discordant_pairs_count": 0,
            "discordant_parameter_pairs": [],
            "evidence_summary": "All evaluated parameters conform to peer population covariance bounds."
        }

    def evaluate_component(
        self,
        cohort_df: pd.DataFrame,
        target_component_id: Any,
        param_keys: List[str],
        checkpoint: Optional[Any] = None,
        id_col: str = "component_id"
    ) -> Dict[str, Any]:
        """
        Evaluates whether target component exhibits abnormal joint parameter behavior
        relative to the empirical cohort distribution at a given checkpoint.
        """
        if cohort_df.empty or len(param_keys) < 2:
            return self.get_nominal_evidence()

        time_col = "checkpoint" if "checkpoint" in cohort_df.columns else ("elapsed_time" if "elapsed_time" in cohort_df.columns else None)
        sub = cohort_df
        if time_col and checkpoint is not None:
            sub = cohort_df[cohort_df[time_col] == checkpoint]
            if sub.empty:
                sub = cohort_df

        # Resolve available numeric parameter columns
        valid_params = [p for p in param_keys if p in sub.columns]
        if len(valid_params) < 2:
            return self.get_nominal_evidence()

        # Extract numeric matrix for cohort
        numeric_df = sub[valid_params].apply(pd.to_numeric, errors="coerce")
        # Keep columns with non-zero variance and sufficient valid rows
        var_mask = numeric_df.var() > 1e-12
        active_params = numeric_df.columns[var_mask].tolist()
        if len(active_params) < 2:
            return self.get_nominal_evidence()

        clean_cohort = numeric_df[active_params].dropna()
        if len(clean_cohort) < 5:
            return self.get_nominal_evidence()

        # Find target component values
        if id_col not in sub.columns:
            return self.get_nominal_evidence()

        target_rows = sub[sub[id_col].astype(str) == str(target_component_id)]
        if target_rows.empty:
            return self.get_nominal_evidence()

        target_vals = target_rows[active_params].iloc[-1].apply(pd.to_numeric, errors="coerce")
        if target_vals.isnull().any():
            return self.get_nominal_evidence()

        target_vec = target_vals.to_numpy(dtype=float)

        # 1. Standardize cohort and target
        means = clean_cohort.mean().to_numpy(dtype=float)
        stds = clean_cohort.std(ddof=1).to_numpy(dtype=float)
        stds = np.where(stds < 1e-8, 1.0, stds)

        z_target = (target_vec - means) / stds

        # 2. Empirical Correlation Matrix (Validated Numerical Relationships)
        corr_matrix = clean_cohort.corr().to_numpy(dtype=float)
        p = len(active_params)

        # Compute regularized Mahalanobis distance in standard space
        try:
            reg_corr = corr_matrix + np.eye(p) * self.regularization
            inv_reg_corr = np.linalg.pinv(reg_corr)
            d_m_sq = float(np.dot(z_target, np.dot(inv_reg_corr, z_target)))
            d_m = float(np.sqrt(max(0.0, d_m_sq)))
        except Exception:
            d_m = float(np.linalg.norm(z_target))

        # Expected Mahalanobis distance is approx sqrt(p)
        expected_dm = np.sqrt(float(p))
        multivariate_z = float(max(0.0, (d_m - expected_dm) / max(1.0, np.sqrt(2.0 * p))))

        # 3. Detect Pairwise Correlation Inversion / Discordance
        discordant_pairs = []
        correlated_pairs_count = 0

        for i in range(p):
            for j in range(i + 1, p):
                r_val = float(corr_matrix[i, j])
                if abs(r_val) >= self.corr_threshold:
                    correlated_pairs_count += 1
                    zi = float(z_target[i])
                    zj = float(z_target[j])

                    # Directional joint divergence
                    if r_val > 0:
                        # Positively coupled: expect same sign; divergence is |zi - zj|
                        divergence = abs(zi - zj)
                        is_inverted = (zi > 1.2 and zj < -1.2) or (zi < -1.2 and zj > 1.2)
                    else:
                        # Negatively coupled: expect opposite sign; divergence is |zi + zj|
                        divergence = abs(zi + zj)
                        is_inverted = (zi > 1.2 and zj > 1.2) or (zi < -1.2 and zj < -1.2)

                    if divergence >= self.joint_z_threshold or (is_inverted and divergence >= 2.0):
                        severity = "HIGH" if divergence >= (self.joint_z_threshold * 1.3) or is_inverted else "MODERATE"
                        p_x = active_params[i]
                        p_y = active_params[j]
                        rel_str = "positive" if r_val > 0 else "inverse"
                        discordant_pairs.append({
                            "param_x": p_x,
                            "param_y": p_y,
                            "cohort_correlation": round(r_val, 4),
                            "z_x": round(zi, 2),
                            "z_y": round(zj, 2),
                            "joint_divergence": round(divergence, 2),
                            "severity": severity,
                            "evidence": (
                                f"Empirical {rel_str} correlation (r={r_val:+.2f}) violated: "
                                f"{p_x} (z={zi:+.2f}) vs {p_y} (z={zj:+.2f}) diverged by {divergence:.2f}σ."
                            )
                        })

        abnormal_detected = (len(discordant_pairs) > 0) or (multivariate_z >= 3.0)

        if abnormal_detected:
            if discordant_pairs:
                top_pair = discordant_pairs[0]
                summary = (
                    f"Abnormal joint behavior detected across {len(discordant_pairs)} correlated parameter pair(s). "
                    f"Primary discordance: {top_pair['param_x']} vs {top_pair['param_y']} "
                    f"(r={top_pair['cohort_correlation']:+.2f}, divergence={top_pair['joint_divergence']}σ). "
                    f"Mahalanobis distance D_M={d_m:.2f}."
                )
            else:
                summary = (
                    f"Abnormal joint behavior detected: Multivariate Mahalanobis distance D_M={d_m:.2f} "
                    f"exceeds cohort covariance boundary (multivariate z={multivariate_z:.2f}σ)."
                )
        else:
            summary = (
                f"Multi-parameter correlation nominal across {len(active_params)} evaluated parameters "
                f"({correlated_pairs_count} validated pairwise relationships). Mahalanobis distance D_M={d_m:.2f}."
            )

        return {
            "status": "DETECTED" if abnormal_detected else "NOMINAL",
            "abnormal_joint_behavior_detected": bool(abnormal_detected),
            "mahalanobis_distance": round(d_m, 4),
            "multivariate_z_score": round(multivariate_z, 4),
            "num_evaluated_parameters": len(active_params),
            "num_correlated_pairs": correlated_pairs_count,
            "discordant_pairs_count": len(discordant_pairs),
            "discordant_parameter_pairs": discordant_pairs,
            "evidence_summary": summary
        }
