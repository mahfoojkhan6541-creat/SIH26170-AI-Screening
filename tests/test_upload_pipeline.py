import os
import io
import json
import pytest
import pandas as pd
import openpyxl
from fastapi.testclient import TestClient
from src.api.service import app

client = TestClient(app)


def test_upload_multi_formats(tmp_path):
    # Prepare sample dataset
    sample_df = pd.DataFrame({
        "ComponentID": [f"TEST_M_{i:03d}" for i in range(1, 21)] * 3,
        "StepID": [0, 72, 168] * 20,
        "Duration_h": [0, 72, 168] * 20,
        "LotNumber": ["LOT-UPLOAD-A"] * 30 + ["LOT-UPLOAD-B"] * 30,
        "DeviceFamily": ["GAN-FET"] * 60,
        "Voltage_Leakage_uA": [0.12 + (i % 5)*0.03 + (0.8 if i == 5 else 0) for i in range(60)],
        "Thermal_Resistance_C_W": [1.45 + (i % 4)*0.1 for i in range(60)],
        "On_Resistance_mOhm": [12.4 + (i % 6)*0.5 for i in range(60)]
    })

    csv_path = str(tmp_path / "test_sample.csv")
    sample_df.to_csv(csv_path, index=False)

    xlsx_path = str(tmp_path / "test_sample.xlsx")
    sample_df.to_excel(xlsx_path, index=False)

    json_path = str(tmp_path / "test_sample.json")
    sample_df.to_json(json_path, orient="records")

    txt_path = str(tmp_path / "test_sample.txt")
    sample_df.to_csv(txt_path, sep="\t", index=False)

    test_files = [
        ("CSV", csv_path),
        ("Excel (XLSX)", xlsx_path),
        ("JSON", json_path),
        ("TXT (Tab-Delimited)", txt_path)
    ]

    for fmt_name, fpath in test_files:
        with open(fpath, "rb") as f:
            file_bytes = f.read()

        # 1. Preview
        files = {"file": (os.path.basename(fpath), file_bytes, "application/octet-stream")}
        prev_resp = client.post("/api/upload/preview", files=files)
        assert prev_resp.status_code == 200, f"Preview failed for {fmt_name}: {prev_resp.text}"
        preview_res = prev_resp.json()
        assert preview_res["total_rows"] == 60
        assert "suggested_mapping" in preview_res

        # 2. Validate
        mapping = {
            "component_id": preview_res["suggested_mapping"]["component_id"],
            "checkpoint": preview_res["suggested_mapping"]["checkpoint"],
            "elapsed_time": preview_res["suggested_mapping"]["elapsed_time"],
            "lot_id": preview_res["suggested_mapping"]["lot_id"],
            "device_type": preview_res["suggested_mapping"]["device_type"],
            "parameters": preview_res["suggested_mapping"]["detected_parameters"]
        }
        val_resp = client.post("/api/upload/validate", json={"saved_path": preview_res["saved_path"], "mapping": mapping})
        assert val_resp.status_code == 200
        val_res = val_resp.json()
        assert val_res["is_valid"] is True

        # 3. Process
        proc_resp = client.post("/api/upload/process", json={
            "saved_path": preview_res["saved_path"],
            "dataset_name": f"User Upload ({fmt_name})",
            "mapping": mapping
        })
        assert proc_resp.status_code == 200
        proc_res = proc_resp.json()
        assert proc_res["total_screened"] == 20
        assert "components" in proc_res
        assert len(proc_res["components"]) == 20
        assert proc_res["total_screened"] == proc_res["pass_count"] + proc_res["review_count"] + proc_res["reject_count"]


@pytest.mark.parametrize("num_rows", [10, 101, 250, 500])
def test_dynamic_upload_arbitrary_sizes(tmp_path, num_rows):
    """
    Verifies that the upload -> screening pipeline is completely dynamic for ANY row count:
    - 10 rows -> 10 screened
    - 101 rows -> 101 screened (even with D2-style columns like MaterialID & feature_1..feature_20)
    - 250 rows -> 250 screened
    - 500 rows -> 500 screened
    Strict Single Source of Truth:
      total_screened == pass_count + review_count + reject_count == len(components) == confusion_matrix total
    """
    # Create dataset with D2-style feature names to ensure no static mock hijacking occurs
    data = {
        "MaterialID": [f"MAT_{i+1:04d}" for i in range(num_rows)],
        "duration_ms": [0.5 + (i * 0.01) for i in range(num_rows)],
    }
    for f in range(1, 21):
        data[f"feature_{f}"] = [0.1 * f + (i % 7) * 0.05 + (2.5 if (i % 23 == 0 and f == 3) else 0.0) for i in range(num_rows)]

    df = pd.DataFrame(data)
    file_path = str(tmp_path / f"test_dynamic_{num_rows}.xlsx")
    df.to_excel(file_path, index=False)

    with open(file_path, "rb") as f:
        file_bytes = f.read()

    # 1. Preview
    files = {"file": (os.path.basename(file_path), file_bytes, "application/octet-stream")}
    prev_resp = client.post("/api/upload/preview", files=files)
    assert prev_resp.status_code == 200
    preview_res = prev_resp.json()
    assert preview_res["total_rows"] == num_rows

    # 2. Validate
    mapping = {
        "component_id": preview_res["suggested_mapping"]["component_id"],
        "checkpoint": preview_res["suggested_mapping"]["checkpoint"],
        "elapsed_time": preview_res["suggested_mapping"]["elapsed_time"],
        "lot_id": preview_res["suggested_mapping"]["lot_id"],
        "device_type": preview_res["suggested_mapping"]["device_type"],
        "parameters": preview_res["suggested_mapping"]["detected_parameters"]
    }
    val_resp = client.post("/api/upload/validate", json={"saved_path": preview_res["saved_path"], "mapping": mapping})
    assert val_resp.status_code == 200
    assert val_resp.json()["is_valid"] is True

    # 3. Process
    proc_resp = client.post("/api/upload/process", json={
        "saved_path": preview_res["saved_path"],
        "dataset_name": f"Dynamic Benchmark Test ({num_rows} rows)",
        "mapping": mapping
    })
    assert proc_resp.status_code == 200
    res = proc_resp.json()

    # Assert Single Source of Truth
    assert res["total_screened"] == num_rows
    assert len(res["components"]) == num_rows
    assert res["pass_count"] + res["review_count"] + res["reject_count"] == num_rows
    assert res["total_screened"] == res["pass_count"] + res["review_count"] + res["reject_count"]

    # Assert Confusion Matrix Integrity
    cm = res["confusion_matrix"]
    assert cm["total"] == num_rows
    assert cm["TN"] + cm["FP"] + cm["FN"] + cm["TP"] == num_rows

    # Assert Histogram Total
    hist_total = sum(b["normal_density"] + b["abnormal_density"] for b in res["histogram_data"])
    assert hist_total == num_rows

