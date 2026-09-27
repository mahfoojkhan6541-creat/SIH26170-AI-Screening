import os
import yaml
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Tuple, Optional


class DataQualityValidator:
    """
    Validates canonical observations against all 12 master decomposition cases
    prescribed by Section 14 of the Generalized Data Pipeline Implementation Guide.

    12 Required Validation Checks:
      1. Missing reading (QUARANTINE)
      2. Partial missingness (WARNING)
      3. NaN/Inf/sensor error (BLOCK)
      4. Duplicate reading (WARNING)
      5. Invalid timestamp/duration (QUARANTINE)
      6. Wrong component ID (BLOCK)
      7. Wrong unit (BLOCK)
      8. Saturation/outlier check for ALL parameters (WARNING)
      9. Noise/flatline check for ALL parameters (WARNING)
      10. Equipment/communication dropout (QUARANTINE)
      11. Out-of-order timestamps/checkpoints (WARNING)
      12. Clock/time mismatch (WARNING)
    """

    RECOGNIZED_UNITS = {
        "arb_norm", "ms_norm", "v", "mv", "uv", "a", "ma", "ua", "na", "pa",
        "degc", "k", "c", "ohm", "kohm", "mohm", "s", "ms", "us", "ns",
        "hours", "h", "hr", "cycles", "hz", "khz", "mhz", "ghz", "%",
        "percent", "ratio", "norm", "arb"
    }

    def __init__(self, rules_config_path: str = "configs/validation/validation_rules.yaml"):
        self.rules_config_path = rules_config_path
        self.rules: Dict[str, Any] = {}
        self.load_rules()

    def load_rules(self):
        if not os.path.exists(self.rules_config_path):
            self.rules = {"rules": {}}
            return
        with open(self.rules_config_path, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
            self.rules = cfg.get("rules", {}) if cfg else {}

    def validate(self, df: pd.DataFrame, param_keys: List[str]) -> Tuple[pd.DataFrame, pd.DataFrame, Dict[str, Any]]:
        """
        Executes all 12 validation rules across all records and measurement parameters.

        Returns:
            - valid_df: records that pass validation or carry only warnings
            - quarantined_df: records quarantined or blocked
            - summary: validation statistics, all 12 checks status, and detailed event log
        """
        all_cases = [
            "case_01_missing_reading",
            "case_02_partial_missingness",
            "case_03_sensor_error",
            "case_04_duplicate_reading",
            "case_05_wrong_timestamp",
            "case_06_wrong_component_id",
            "case_07_wrong_unit",
            "case_08_measurement_saturation",
            "case_09_sensor_noise",
            "case_10_communication_failure",
            "case_11_out_of_order_records",
            "case_12_clock_mismatch"
        ]

        if df.empty:
            empty_checks = {}
            for c in all_cases:
                empty_checks[c] = "PASS"
                empty_checks[c[:7]] = "PASS"
            empty_summary = {
                "total_evaluated": 0,
                "total_records_checked": 0,
                "valid_records": 0,
                "quarantined_records": 0,
                "blocked_records": 0,
                "quarantine_rate": 0.0,
                "events_detected": [],
                "all_checks_status": empty_checks
            }
            return df.copy(), df.copy(), empty_summary

        severities = pd.Series("VALID", index=df.index, dtype=object)
        reasons = pd.Series("", index=df.index, dtype=object)
        events: List[Dict[str, Any]] = []

        def log_issue(mask: pd.Series, case_id: str, case_name: str, severity: str, action: str, reason_text: str):
            count = int(mask.sum())
            if count > 0:
                events.append({
                    "case_id": case_id,
                    "name": case_name,
                    "severity": severity,
                    "action": action,
                    "affected_records": count,
                    "reason": reason_text
                })
                # Vectorized update of record-level severities: BLOCK > QUARANTINE > WARNING > VALID
                if severity == "BLOCK":
                    severities.loc[mask] = "BLOCK"
                elif severity == "QUARANTINE":
                    upd_mask = mask & (severities != "BLOCK")
                    severities.loc[upd_mask] = "QUARANTINE"
                elif severity == "WARNING":
                    upd_mask = mask & (severities == "VALID")
                    severities.loc[upd_mask] = "WARNING"

                # Vectorized update of reasons
                empty_mask = mask & (reasons == "")
                reasons.loc[empty_mask] = reason_text
                non_empty_mask = mask & (reasons != "")
                reasons.loc[non_empty_mask] = reasons.loc[non_empty_mask] + "; " + reason_text

        # -----------------------------------------------------------------
        # 1. Case 06: Wrong Component ID (BLOCK)
        # -----------------------------------------------------------------
        if "component_id" in df.columns:
            id_str = df["component_id"].astype(str).str.strip().str.upper()
            bad_id_mask = df["component_id"].isnull() | id_str.isin(["", "UNKNOWN", "NAN", "NONE", "NULL"])
        else:
            bad_id_mask = pd.Series(True, index=df.index)
        log_issue(
            bad_id_mask,
            "case_06_wrong_component_id",
            "Wrong Component ID Check",
            "BLOCK",
            "BLOCK",
            "Missing, blank, or malformed component identifier"
        )

        # -----------------------------------------------------------------
        # 2. Case 01: Missing Reading (QUARANTINE)
        # -----------------------------------------------------------------
        valid_params = [p for p in param_keys if p in df.columns]
        if valid_params:
            param_all_nan_mask = df[valid_params].isnull().all(axis=1)
        else:
            param_all_nan_mask = pd.Series(True, index=df.index)
        log_issue(
            param_all_nan_mask,
            "case_01_missing_reading",
            "Missing Reading Check",
            "QUARANTINE",
            "QUARANTINE",
            "All measurement parameters are missing for this record"
        )

        # -----------------------------------------------------------------
        # 3. Case 02: Partial Missingness (WARNING)
        # -----------------------------------------------------------------
        if valid_params:
            param_any_nan_mask = df[valid_params].isnull().any(axis=1)
            partial_mask = param_any_nan_mask & (~param_all_nan_mask)
        else:
            partial_mask = pd.Series(False, index=df.index)
        log_issue(
            partial_mask,
            "case_02_partial_missingness",
            "Partial Missingness Check",
            "WARNING",
            "WARNING",
            "Partial missingness: some parameter values are missing in record"
        )

        # -----------------------------------------------------------------
        # 4. Case 03: NaN / Inf / Sensor Error (BLOCK)
        # -----------------------------------------------------------------
        param_inf_mask = pd.Series(False, index=df.index)
        for p in valid_params:
            num_s = pd.to_numeric(df[p], errors="coerce")
            param_inf_mask |= np.isinf(num_s) | (df[p].notnull() & num_s.isnull())
        log_issue(
            param_inf_mask,
            "case_03_sensor_error",
            "Sensor Error Check",
            "BLOCK",
            "BLOCK",
            "Measurement parameter contains infinite or corrupted non-numeric value"
        )

        # -----------------------------------------------------------------
        # 5. Case 04: Duplicate Reading (WARNING)
        # -----------------------------------------------------------------
        dup_subset = []
        if "component_id" in df.columns:
            dup_subset.append("component_id")
        if "checkpoint" in df.columns:
            dup_subset.append("checkpoint")
        if "elapsed_time" in df.columns:
            dup_subset.append("elapsed_time")
        dup_subset.extend(valid_params)

        if dup_subset:
            dup_mask = df.duplicated(subset=dup_subset, keep="first")
        else:
            dup_mask = pd.Series(False, index=df.index)
        log_issue(
            dup_mask,
            "case_04_duplicate_reading",
            "Duplicate Reading Check",
            "WARNING",
            "WARNING",
            "Exact duplicate measurement record detected for component and timestamp"
        )

        # -----------------------------------------------------------------
        # 6. Case 05: Invalid Timestamp / Duration (QUARANTINE)
        # -----------------------------------------------------------------
        bad_time_mask = pd.Series(False, index=df.index)
        if "checkpoint" in df.columns:
            cp_num = pd.to_numeric(df["checkpoint"], errors="coerce")
            bad_time_mask |= df["checkpoint"].isnull() | np.isinf(cp_num) | cp_num.isnull()
        if "elapsed_time" in df.columns:
            el_num = pd.to_numeric(df["elapsed_time"], errors="coerce")
            bad_time_mask |= df["elapsed_time"].isnull() | np.isinf(el_num) | el_num.isnull() | (el_num < 0)
        log_issue(
            bad_time_mask,
            "case_05_wrong_timestamp",
            "Wrong Timestamp Check",
            "QUARANTINE",
            "QUARANTINE",
            "Invalid timestamp: checkpoint or elapsed time is missing, infinite, non-numeric, or negative"
        )

        # -----------------------------------------------------------------
        # 7. Case 07: Wrong Unit (BLOCK)
        # -----------------------------------------------------------------
        bad_unit_mask = pd.Series(False, index=df.index)
        unit_col = None
        for col in ["unit", "units", "canonical_unit", "measurement_unit"]:
            if col in df.columns:
                unit_col = col
                break
        if unit_col:
            u_series = df[unit_col].astype(str).str.strip().str.lower()
            bad_unit_mask = df[unit_col].isnull() | (~u_series.isin(self.RECOGNIZED_UNITS))
        log_issue(
            bad_unit_mask,
            "case_07_wrong_unit",
            "Wrong Unit Check",
            "BLOCK",
            "BLOCK",
            "Unrecognized or invalid unit declaration detected"
        )

        # -----------------------------------------------------------------
        # 8. Case 08: Measurement Saturation Check for ALL parameters (WARNING)
        # -----------------------------------------------------------------
        for p in valid_params:
            s = pd.to_numeric(df[p], errors="coerce").dropna()
            if len(s) > 1:
                std_val = float(s.std())
                mean_val = float(s.mean())
                med_val = float(s.median())
                mad_val = float((s - med_val).abs().median())
                robust_sigma = 1.4826 * mad_val
                effective_sigma = robust_sigma if robust_sigma > 1e-12 else std_val
                center = med_val if robust_sigma > 1e-12 else mean_val
                if effective_sigma > 1e-12:
                    sat_mask = (pd.to_numeric(df[p], errors="coerce") - center).abs() > (6.0 * effective_sigma)
                    log_issue(
                        sat_mask,
                        "case_08_measurement_saturation",
                        f"Measurement Saturation ({p})",
                        "WARNING",
                        "WARNING",
                        f"Measurement in parameter '{p}' exceeds 6-sigma statistical saturation boundary"
                    )

        # -----------------------------------------------------------------
        # 9. Case 09: Noise / Flatline Check for ALL parameters (WARNING)
        # -----------------------------------------------------------------
        for p in valid_params:
            s = pd.to_numeric(df[p], errors="coerce").dropna()
            # 1. Dataset-wide flatline
            if len(s) > 1 and float(s.std()) < 1e-12:
                flat_mask = pd.Series(True, index=df.index)
                log_issue(
                    flat_mask,
                    "case_09_sensor_noise",
                    f"Sensor Noise / Flatline ({p})",
                    "WARNING",
                    "WARNING",
                    f"Zero variance (dead sensor flatline) detected across dataset in parameter '{p}'"
                )
            # 2. Component-level flatline (for components with >= 4 records where overall std > 1e-6)
            elif len(s) > 1 and float(s.std()) > 1e-6 and "component_id" in df.columns:
                p_num = pd.to_numeric(df[p], errors="coerce")
                comp_stds = p_num.groupby(df["component_id"]).transform("std")
                comp_counts = p_num.groupby(df["component_id"]).transform("count")
                comp_flat_mask = (comp_counts >= 4) & (comp_stds < 1e-12)
                log_issue(
                    comp_flat_mask,
                    "case_09_sensor_noise",
                    f"Sensor Noise / Component Flatline ({p})",
                    "WARNING",
                    "WARNING",
                    f"Component-level dead sensor flatline (zero variance across >=4 checkpoints) in parameter '{p}'"
                )

        # -----------------------------------------------------------------
        # 10. Case 10: Equipment / Communication Dropout (QUARANTINE)
        # -----------------------------------------------------------------
        dropout_mask = pd.Series(False, index=df.index)
        if "component_id" in df.columns and ("checkpoint" in df.columns or "elapsed_time" in df.columns):
            time_col = "elapsed_time" if "elapsed_time" in df.columns else "checkpoint"
            for cid, grp in df.groupby("component_id"):
                if len(grp) >= 3:
                    t_vals = pd.to_numeric(grp[time_col], errors="coerce").dropna().values
                    if len(t_vals) >= 3:
                        deltas = np.diff(t_vals)
                        pos_deltas = deltas[deltas > 0]
                        if len(pos_deltas) >= 2:
                            med_step = float(np.median(pos_deltas))
                            if med_step > 0:
                                gap_indices = np.where(deltas > 3.0 * med_step)[0]
                                for g_idx in gap_indices:
                                    row_idx = grp.index[g_idx + 1]
                                    dropout_mask.at[row_idx] = True
        log_issue(
            dropout_mask,
            "case_10_communication_failure",
            "Communication Failure Check",
            "QUARANTINE",
            "QUARANTINE",
            "Communication/equipment dropout: unexpected telemetry gap exceeding 3x expected sampling step"
        )

        # -----------------------------------------------------------------
        # 11. Case 11: Out-of-Order Timestamps / Checkpoints (WARNING)
        # -----------------------------------------------------------------
        out_of_order_mask = pd.Series(False, index=df.index)
        if "component_id" in df.columns and ("checkpoint" in df.columns or "elapsed_time" in df.columns):
            time_col = "checkpoint" if "checkpoint" in df.columns else "elapsed_time"
            t_num = pd.to_numeric(df[time_col], errors="coerce")
            prev_t = t_num.groupby(df["component_id"]).shift(1)
            out_of_order_mask = (t_num < prev_t) & t_num.notnull() & prev_t.notnull()
        log_issue(
            out_of_order_mask,
            "case_11_out_of_order_records",
            "Out of Order Records Check",
            "WARNING",
            "WARNING",
            "Chronological reversal: timestamps arrived out of chronological order"
        )

        # -----------------------------------------------------------------
        # 12. Case 12: Clock / Time Mismatch (WARNING)
        # -----------------------------------------------------------------
        clock_mismatch_mask = pd.Series(False, index=df.index)
        if "component_id" in df.columns and "checkpoint" in df.columns and "elapsed_time" in df.columns:
            cp_num = pd.to_numeric(df["checkpoint"], errors="coerce")
            el_num = pd.to_numeric(df["elapsed_time"], errors="coerce")
            prev_cp = cp_num.groupby(df["component_id"]).shift(1)
            prev_el = el_num.groupby(df["component_id"]).shift(1)
            d_cp = cp_num - prev_cp
            d_el = el_num - prev_el
            valid_d = prev_cp.notnull() & prev_el.notnull() & cp_num.notnull() & el_num.notnull()
            clock_mismatch_mask = valid_d & (((d_cp > 0) & (d_el < 0)) | ((d_cp < 0) & (d_el > 0)))
        log_issue(
            clock_mismatch_mask,
            "case_12_clock_mismatch",
            "Clock Mismatch Check",
            "WARNING",
            "WARNING",
            "Clock mismatch: temporal inconsistency between discrete checkpoint and instrument elapsed duration"
        )

        # -----------------------------------------------------------------
        # Summary & All 12 Checks Status Dictionary
        # -----------------------------------------------------------------
        all_cases = [
            "case_01_missing_reading",
            "case_02_partial_missingness",
            "case_03_sensor_error",
            "case_04_duplicate_reading",
            "case_05_wrong_timestamp",
            "case_06_wrong_component_id",
            "case_07_wrong_unit",
            "case_08_measurement_saturation",
            "case_09_sensor_noise",
            "case_10_communication_failure",
            "case_11_out_of_order_records",
            "case_12_clock_mismatch"
        ]

        all_checks_status = {}
        for c in all_cases:
            short_c = c[:7]
            matching_events = [e for e in events if e["case_id"].startswith(c)]
            if matching_events:
                actions = [e["action"] for e in matching_events]
                if "BLOCK" in actions:
                    status = "BLOCK"
                elif "QUARANTINE" in actions:
                    status = "QUARANTINE"
                elif "WARNING" in actions:
                    status = "WARNING"
                else:
                    status = "PASS"
            else:
                status = "PASS"
            all_checks_status[c] = status
            all_checks_status[short_c] = status

        # Attach validation metadata to output dataframes
        validated_df = df.copy()
        validated_df["quality_status"] = severities
        validated_df["quality_reasons"] = reasons

        is_quarantine = severities.isin(["QUARANTINE", "BLOCK"])
        quarantined_df = validated_df[is_quarantine].copy()
        valid_df = validated_df[~is_quarantine].copy()

        summary = {
            "total_evaluated": len(df),
            "total_records_checked": len(df),
            "valid_records": len(valid_df),
            "quarantined_records": int(is_quarantine.sum()),
            "blocked_records": int((severities == "BLOCK").sum()),
            "quarantine_rate": float(len(quarantined_df) / max(len(df), 1)),
            "events_detected": events,
            "all_checks_status": all_checks_status
        }

        return valid_df, quarantined_df, summary
