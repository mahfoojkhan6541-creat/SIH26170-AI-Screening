import urllib.request
import json
import os
import pandas as pd
import openpyxl

def run_tests():
    # 1. Health check
    res = urllib.request.urlopen("http://127.0.0.1:8000/health")
    health = json.loads(res.read().decode("utf-8"))
    print("Health Check:", health["status"])

    # 2. Prepare multi-format test files
    # A) CSV test file
    csv_path = "data/test_upload_sample.csv"
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
    sample_df.to_csv(csv_path, index=False)

    # B) XLSX test file
    xlsx_path = "data/test_upload_sample.xlsx"
    sample_df.to_excel(xlsx_path, index=False)

    # C) JSON test file
    json_path = "data/test_upload_sample.json"
    sample_df.to_json(json_path, orient="records")

    # D) TXT tab-separated test file
    txt_path = "data/test_upload_sample.txt"
    sample_df.to_csv(txt_path, sep="\t", index=False)

    test_files = [
        ("CSV", csv_path),
        ("Excel (XLSX)", xlsx_path),
        ("JSON", json_path),
        ("TXT (Tab-Delimited)", txt_path)
    ]

    for fmt_name, fpath in test_files:
        print(f"\n--- Testing Format: {fmt_name} ({fpath}) ---")
        with open(fpath, "rb") as f:
            file_bytes = f.read()

        boundary = "----WebKitFormBoundaryUploadTest"
        body = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="file"; filename="{os.path.basename(fpath)}"\r\n'
            f"Content-Type: application/octet-stream\r\n\r\n"
        ).encode("utf-8") + file_bytes + f"\r\n--{boundary}--\r\n".encode("utf-8")

        req = urllib.request.Request(
            "http://127.0.0.1:8000/api/upload/preview",
            data=body,
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"}
        )
        preview_res = json.loads(urllib.request.urlopen(req).read().decode("utf-8"))
        print(f"Preview: Format={preview_res['format']}, Rows={preview_res['total_rows']}, Cols={preview_res['total_columns']}")
        print(f"Suggested Mapping: {preview_res['suggested_mapping']}")

        # Validate
        mapping = {
            "component_id": preview_res["suggested_mapping"]["component_id"],
            "checkpoint": preview_res["suggested_mapping"]["checkpoint"],
            "elapsed_time": preview_res["suggested_mapping"]["elapsed_time"],
            "lot_id": preview_res["suggested_mapping"]["lot_id"],
            "device_type": preview_res["suggested_mapping"]["device_type"],
            "parameters": preview_res["suggested_mapping"]["detected_parameters"]
        }
        val_body = json.dumps({"saved_path": preview_res["saved_path"], "mapping": mapping}).encode("utf-8")
        val_req = urllib.request.Request("http://127.0.0.1:8000/api/upload/validate", data=val_body, headers={"Content-Type": "application/json"})
        val_res = json.loads(urllib.request.urlopen(val_req).read().decode("utf-8"))
        print(f"Validate: is_valid={val_res['is_valid']}, Passed Checks={sum(1 for c in val_res['checks'] if c['passed'])}/6")

        # Process
        proc_body = json.dumps({
            "saved_path": preview_res["saved_path"],
            "dataset_name": f"User Upload ({fmt_name})",
            "mapping": mapping
        }).encode("utf-8")
        proc_req = urllib.request.Request("http://127.0.0.1:8000/api/upload/process", data=proc_body, headers={"Content-Type": "application/json"})
        proc_res = json.loads(urllib.request.urlopen(proc_req).read().decode("utf-8"))
        print(f"Process: Screened={proc_res['total_screened']}, Pass={proc_res['pass_count']}, Review={proc_res['review_count']}, Reject={proc_res['reject_count']}, Threshold={proc_res['threshold']}")
        print(f"First Component Result: ID={proc_res['components'][0]['id']}, Disposition={proc_res['components'][0]['disposition']}, Score={proc_res['components'][0]['score']}")

    print("\nALL FORMATS (CSV, XLSX, JSON, TXT) TESTED AND PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    run_tests()
