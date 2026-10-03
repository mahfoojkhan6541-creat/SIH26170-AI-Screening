"""
Backend Architecture: Final ISRO-Focused 13-Stage Data Pipeline (SIH26170)
==========================================================================
Visually and programmatically mapped to the exact execution sequence:

  01_Input                 -> Raw authentic screening datasets & benchmark configs
  02_Intake                -> Multi-format intake adapters & dataset registry
  03_Profiling             -> Automated structural profiling & compatibility evaluation
  04_Context_Mapping       -> Context/semantic mapping & canonical unit conversion
  05_Data_Quality          -> 12-check aerospace quality gate & quarantine isolation
  06_Confounders           -> Common-mode shift detection & time alignment
  07_Canonical             -> Standardized canonical internal representation
  08_Reference_Population  -> Peer grouping with strict target exclusion & anti-leakage
  09_Features              -> Behavioral feature engineering, drift dynamics & relative metrics
  10_Models                -> Two model branches (10A: Isolation Forest, 10B: GPR Trajectory)
  11_Evidence              -> Multi-stream limit, drift, forecast & correlation evaluation
  12_Decision_Explanation  -> Conservative decision rules & explainable AI (SHAP attributions)
  13_QA_Audit_API          -> SQLite provenance audit storage & FastAPI serving endpoints
"""
import sys
import importlib
from typing import List, Tuple

# Execution sequence stages and their Python-safe module aliases
STAGES: List[Tuple[str, List[str]]] = [
    ("01_Input", ["stage_01_input", "input_data"]),
    ("02_Intake", ["stage_02_intake", "intake", "ingestion"]),
    ("03_Profiling", ["stage_03_profiling", "profiling", "compatibility"]),
    ("04_Context_Mapping", ["stage_04_context_mapping", "context_mapping", "mapping"]),
    ("05_Data_Quality", ["stage_05_data_quality", "data_quality", "validation"]),
    ("06_Confounders", ["stage_06_confounders", "confounders"]),
    ("07_Canonical", ["stage_07_canonical", "canonical"]),
    ("08_Reference_Population", ["stage_08_reference_population", "reference_population", "grouping"]),
    ("09_Features", ["stage_09_features", "features"]),
    ("10_Models", ["stage_10_models", "models"]),
    ("11_Evidence", ["stage_11_evidence", "evidence"]),
    ("12_Decision_Explanation", ["stage_12_decision_explanation", "decision_explanation", "decision", "explanation"]),
    ("13_QA_Audit_API", ["stage_13_qa_audit_api", "qa_audit_api", "api", "audit", "state"]),
]

# Sequential loading ensuring each stage is fully registered for subsequent stages
for folder, aliases in STAGES:
    real_mod = importlib.import_module(f"backend.{folder}")
    for a in aliases:
        sys.modules[f"backend.{a}"] = real_mod
        setattr(sys.modules[__name__], a, real_mod)
