import os

# Project root directory determination
CORE_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(CORE_DIR)
ROOT_DIR = os.path.dirname(BACKEND_DIR)

# Canonical path resolvers with robust fallbacks
DATA_DIR = os.path.join(ROOT_DIR, "data")
CONFIG_DIR = os.path.join(ROOT_DIR, "configs")
MODELS_DIR = os.path.join(ROOT_DIR, "models")
FEATURES_DIR = os.path.join(ROOT_DIR, "features")
RESULTS_DIR = os.path.join(ROOT_DIR, "results")
FRONTEND_DIR = os.path.join(ROOT_DIR, "frontend")
DASHBOARD_DIR = os.path.join(ROOT_DIR, "dashboard")
UPLOAD_DIR = os.path.join(DATA_DIR, "uploads")
AUDIT_DB_PATH = os.path.join(DATA_DIR, "audit_traceability.db")

# Stage-specific folders
STAGE_01_INPUT_DIR = os.path.join(BACKEND_DIR, "01_Input")
STAGE_02_INTAKE_DIR = os.path.join(BACKEND_DIR, "02_Intake")
STAGE_03_PROFILING_DIR = os.path.join(BACKEND_DIR, "03_Profiling")
STAGE_04_CONTEXT_MAPPING_DIR = os.path.join(BACKEND_DIR, "04_Context_Mapping")
STAGE_05_DATA_QUALITY_DIR = os.path.join(BACKEND_DIR, "05_Data_Quality")
STAGE_06_CONFOUNDERS_DIR = os.path.join(BACKEND_DIR, "06_Confounders")
STAGE_07_CANONICAL_DIR = os.path.join(BACKEND_DIR, "07_Canonical")
STAGE_08_REFERENCE_POPULATION_DIR = os.path.join(BACKEND_DIR, "08_Reference_Population")
STAGE_09_FEATURES_DIR = os.path.join(BACKEND_DIR, "09_Features")
STAGE_10_MODELS_DIR = os.path.join(BACKEND_DIR, "10_Models")
STAGE_11_EVIDENCE_DIR = os.path.join(BACKEND_DIR, "11_Evidence")
STAGE_12_DECISION_EXPLANATION_DIR = os.path.join(BACKEND_DIR, "12_Decision_Explanation")
STAGE_13_QA_AUDIT_API_DIR = os.path.join(BACKEND_DIR, "13_QA_Audit_API")

os.makedirs(UPLOAD_DIR, exist_ok=True)
