import json
import sys
import os
sys.path.insert(0, os.path.abspath("."))
from fastapi.testclient import TestClient
from src.api.service import app

def verify_all():
    client = TestClient(app)

    print("[1] Health check (/health)...")
    res = client.get("/health")
    assert res.status_code == 200, res.text
    print("    Health status:", res.json())

    print("\n[2] Master Workspace payload (/api/workspace)...")
    res = client.get("/api/workspace")
    assert res.status_code == 200, res.text
    ws = res.json()
    scores = ws.get("scores", [])
    print(f"    Retrieved {len(scores)} screened components from authentic database/workspace.")
    assert len(scores) > 0, "No components in workspace"
    print(f"    Sample component ID: {scores[0].get('id')}, disposition: {scores[0].get('disposition')}")

    print("\n[3] Model registry (/api/models/registry)...")
    res = client.get("/api/models/registry")
    assert res.status_code == 200, res.text
    models = res.json()
    print("    Registered models:", list(models.keys()))
    assert "D2" in models and "NASA_GPR_v2" in models
    assert models["D2"]["model_version"] == "v2_clean_split"
    assert models["D2"]["metrics"]["recall"] == 0.9623
    assert models["NASA_GPR_v2"]["version"] == "v2_physical_device_clean"
    assert models["NASA_GPR_v2"]["held_out_test_device"] == "Device_4"

    print("\n[4] End-to-End Dataset Analysis (/analyze)...")
    payload = {
        "dataset_id": "D2",
        "config_version": "default_v1",
        "sample_limit": 5
    }
    res = client.post("/analyze", json=payload)
    assert res.status_code == 200, res.text
    ana = res.json()
    run_id = ana.get("run_id")
    print(f"    Run executed: {run_id}, status: {ana.get('status')}")
    sample_results = ana.get("sample_results", [])
    assert len(sample_results) > 0
    target_comp = sample_results[0]["component_id"]
    print(f"    Sample analyzed component: {target_comp}")
    print(f"    Anomaly score: {sample_results[0].get('anomaly_score')}")
    print(f"    Recommendation: {sample_results[0].get('recommendation')}")
    print(f"    Explanation: {sample_results[0].get('reason')}")

    print(f"\n[5] Human QA Final Disposition (/audit/qa-action) for run_id={run_id}...")
    qa_payload = {
        "component_id": str(target_comp),
        "run_id": run_id,
        "checkpoint": 168.0,
        "ai_recommendation": sample_results[0].get("recommendation", "PASS"),
        "human_action": "CONFIRM_REJECT",
        "reviewer_id": "QA_INSP_ISRO_007",
        "notes": "Latent leakage acceleration confirmed against qualification baseline."
    }
    res = client.post("/audit/qa-action", json=qa_payload)
    assert res.status_code == 200, res.text
    qa_res = res.json()
    print("    QA Action recorded in SQLite:", qa_res.get("status"))

    print(f"\n[6] End-to-End Provenance Traceability (/api/components/{target_comp}/trace)...")
    res = client.get(f"/api/components/{target_comp}/trace")
    assert res.status_code == 200, res.text
    trace = res.json()
    print("    Provenance chain:", trace.get("provenance_chain"))
    print("    Model version:", trace.get("model_version"))
    print("    Human QA status:", trace.get("human_qa", {}).get("status"))
    print("    Inspector action:", trace.get("human_qa", {}).get("human_action"))
    print("    Inspector ID:", trace.get("human_qa", {}).get("reviewer_id"))
    assert trace.get("verified_traceable") is True
    assert trace.get("human_qa", {}).get("status") == "AUTHORIZED"

    print(f"\n[7] Historical Run Query (/audit/{run_id})...")
    res = client.get(f"/audit/{run_id}")
    assert res.status_code == 200, res.text
    audit_data = res.json()
    print("    Audit run ID:", audit_data.get("run_id"))
    print("    Audit records retrieved:", len(audit_data.get("decisions", [])))

    print("\n[SUCCESS] ALL END-TO-END DEMO FLOWS VERIFIED SUCCESSFULLY!")

if __name__ == "__main__":
    verify_all()
