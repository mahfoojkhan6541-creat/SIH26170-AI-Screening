"""
Stage 01: Input Data
Primary authentic burn-in and screening data for ISRO evaluation,
plus development/validation benchmarks (D1, D2, NASA, SECOM).
"""
import os
from backend.core.paths import DATA_DIR, STAGE_01_INPUT_DIR

RAW_DATA_DIR = os.path.join(STAGE_01_INPUT_DIR, "raw_data")
CONFIGS_DIR = os.path.join(STAGE_01_INPUT_DIR, "configs")

def _resolve_data_path(*candidates: str) -> str:
    for c in candidates:
        full_path = os.path.join(DATA_DIR, c)
        if os.path.exists(full_path):
            return full_path
    return os.path.join(DATA_DIR, candidates[0])

AUTHENTIC_DATASETS = {
    "D1": _resolve_data_path("D1.csv", "D1_dataset.csv"),
    "D2": _resolve_data_path("D2.csv", "D2_dataset.csv"),
    "ISRO": _resolve_data_path("ISRO_dataset.csv", "NASA.csv"),
    "NASA": _resolve_data_path("NASA.csv", "NASA_steadyState_raw.csv"),
    "NASA_MAT": _resolve_data_path("NASA_PCoE_Dataset.mat"),
    "SECOM": _resolve_data_path("SECOM_dataset.csv"),
}

__all__ = ["AUTHENTIC_DATASETS", "RAW_DATA_DIR", "CONFIGS_DIR"]
