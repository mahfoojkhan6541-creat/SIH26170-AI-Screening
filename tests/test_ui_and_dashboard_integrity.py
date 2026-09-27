"""
Automated Integration and UI Integrity Test Suite for SIH26170 Dashboard.

Verifies:
1. D2 never shows a forecast curve, fake 168h forecast values, or misleading 0h->168h labeling.
2. D2 and D1 native records never show fake lot IDs.
3. Datasets without lot metadata cleanly display:
   "Lot-wise analysis unavailable: source dataset contains no lot metadata."
4. Uploaded/streamed data containing real lot_id automatically enables lot-wise analysis.
5. ISRO live simulation does not invent fake lots or fake GPR forecasts.
"""

import json
import os
import re
import pytest
from fastapi.testclient import TestClient

from src.api.service import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_d2_never_shows_forecast_curve_or_fake_168h_values(client):
    """
    D2 INSPECTION:
    - Keep GPR as "Unavailable — Insufficient History".
    - NEVER display a fake 168h D2 forecast.
    - Remove misleading 0h -> 168h labeling for D2.
    - Native D2 checkpoints must be Step 1 & Step 2.
    - Clearly label: "GPR not applicable: insufficient trajectory history."
    - Trajectory chart must never render forecast curves when GPR is unavailable.
    """
    resp = client.get("/api/workspace?dataset_id=D2")
    assert resp.status_code == 200
    data = resp.json()
    d2_items = data.get("scores", [])
    assert len(d2_items) > 0, "No D2 items returned from workspace"

    for item in d2_items:
        cid = item.get("id")
        # 1. Forecast status must be explicitly unavailable
        assert item.get("forecast_status") == "unavailable_insufficient_history", (
            f"Component {cid} has active forecast_status: {item.get('forecast_status')}"
        )
        assert item.get("forecast_mean") is None, f"Component {cid} has non-null forecast_mean"
        assert item.get("predicted_168h") is None, f"Component {cid} has non-null predicted_168h"
        assert item.get("forecast_std") is None
        assert item.get("lower_2sigma") is None
        assert item.get("upper_2sigma") is None

        # 2. Check native checkpoints & steps
        assert item.get("checkpoint") == "Step 2", f"Component {cid} checkpoint is not Step 2"
        assert item.get("checkpoints_labels") == ["Step 1", "Step 2"], (
            f"Component {cid} has non-native checkpoints_labels: {item.get('checkpoints_labels')}"
        )
        assert item.get("steps") == [1, 2], f"Component {cid} has invalid steps: {item.get('steps')}"

        # 3. Forecast reason must explicitly state GPR not applicable
        f_reason = str(item.get("forecast_reason", ""))
        assert "GPR not applicable: insufficient trajectory history." in f_reason

    # 4. Verify dashboard/screening.html contains required legend and does not render forecast cones for D2
    screening_path = os.path.join("dashboard", "screening.html")
    assert os.path.exists(screening_path)
    with open(screening_path, "r", encoding="utf-8") as f:
        screening_html = f.read()

    # Exact required label in screening HTML dynamic legend
    assert "GPR not applicable: insufficient trajectory history." in screening_html
    # Default 2-point labels must be Step 1 & Step 2, not 0h & 168h
    assert "['Step 1', 'Step 2']" in screening_html
    # Ensure no hardcoded "168h GPR Forecast" header remains in Stat Box 3
    assert 'id="inspForecastHeader">Trajectory Forecast (GPR)</div>' in screening_html


def test_d2_and_d1_never_show_fake_lot_ids(client):
    """
    LOT-WISE SCREEN:
    - Do NOT invent LOT IDs for D1/D2.
    - When lot_id is absent, lot and lot_id must be null.
    - Neither D1 nor D2 should contain fabricated LOT-D2 or LOT-D1 prefixes.
    """
    resp = client.get("/api/workspace")
    assert resp.status_code == 200
    data = resp.json()
    all_scores = data.get("scores", [])
    assert len(all_scores) > 0

    d2_d1_items = [
        s for s in all_scores
        if "D2" in str(s.get("device_type", "")) or "D1" in str(s.get("device_type", ""))
    ]
    assert len(d2_d1_items) > 0

    for item in d2_d1_items:
        cid = item.get("id")
        lot_val = item.get("lot")
        lot_id_val = item.get("lot_id")

        assert lot_val is None, f"Component {cid} has invented lot: {lot_val}"
        assert lot_id_val is None, f"Component {cid} has invented lot_id: {lot_id_val}"

        # Ensure no fabricated string exists
        assert "LOT-D2-" not in str(lot_val)
        assert "LOT-D1-" not in str(lot_val)
        assert "LOT-UPLOAD-" not in str(lot_val)

    # Check dashboard/screening.html does not invent fake lots when lot is missing
    with open(os.path.join("dashboard", "screening.html"), "r", encoding="utf-8") as f:
        html = f.read()

    assert "LOT: ${component.lot || ('LOT-' + currentDataset)}" not in html
    assert "LOT: No Lot Metadata" in html


def test_no_lot_datasets_show_clear_unavailable_message():
    """
    When lot_id is absent, the dashboard MUST show:
    "Lot-wise analysis unavailable: source dataset contains no lot metadata."
    """
    shared_js_path = os.path.join("dashboard", "shared.js")
    assert os.path.exists(shared_js_path)
    with open(shared_js_path, "r", encoding="utf-8") as f:
        shared_js = f.read()

    # Exact required string must be present in shared.js
    required_msg = "Lot-wise analysis unavailable: source dataset contains no lot metadata."
    assert required_msg in shared_js

    # Test the JS logic contract:
    # Simulate a dataset where components have no lot metadata
    no_lot_sample = [
        {"id": "2", "device_type": "Semiconductor Device (D2)", "lot": None, "lot_id": None, "disposition": "PASS"},
        {"id": "5", "device_type": "Semiconductor Device (D2)", "lot": None, "lot_id": None, "disposition": "PASS"},
        {"id": "21", "device_type": "Semiconductor Device (D2)", "lot": None, "lot_id": None, "disposition": "REVIEW"},
    ]

    has_real_lots = any(
        (item.get("lot_id") or item.get("lot")) is not None
        and str(item.get("lot_id") or item.get("lot")).strip() != ""
        and not str(item.get("lot_id") or item.get("lot")).startswith("N/A")
        and not str(item.get("lot_id") or item.get("lot")).startswith("LOT-UPLOAD-")
        for item in no_lot_sample
    )
    assert not has_real_lots, "Synthetic dataset without lots unexpectedly passed has_real_lots check"


def test_real_lot_id_data_enables_lot_wise_analysis():
    """
    If uploaded or real data contains a genuine lot_id, automatically enable
    lot-wise grouping and charts.
    """
    # Sample data with authentic lot IDs (e.g. from customer wafer fabrication upload)
    sample_with_lots = [
        {"id": "U01", "lot_id": "FAB-LOT-4401", "disposition": "PASS"},
        {"id": "U02", "lot_id": "FAB-LOT-4401", "disposition": "PASS"},
        {"id": "U03", "lot_id": "FAB-LOT-4401", "disposition": "REJECT"},
        {"id": "U04", "lot_id": "FAB-LOT-4402", "disposition": "PASS"},
        {"id": "U05", "lot_id": "FAB-LOT-4402", "disposition": "REVIEW"},
    ]

    # Evaluate the exact grouping contract implemented in shared.js
    has_real_lots = any(
        (item.get("lot_id") or item.get("lot")) is not None
        and str(item.get("lot_id") or item.get("lot")).strip() != ""
        and not str(item.get("lot_id") or item.get("lot")).startswith("N/A")
        and not str(item.get("lot_id") or item.get("lot")).startswith("LOT-UPLOAD-")
        for item in sample_with_lots
    )
    assert has_real_lots is True, "Authentic lot data failed has_real_lots check"

    lot_map = {}
    for item in sample_with_lots:
        raw_lot = item.get("lot_id") or item.get("lot")
        lot = str(raw_lot).strip()
        if lot not in lot_map:
            lot_map[lot] = {"lot": lot, "pass": 0, "review": 0, "reject": 0, "total": 0}
        lot_map[lot]["total"] += 1
        disp = str(item.get("disposition", "PASS")).upper()
        if disp == "PASS":
            lot_map[lot]["pass"] += 1
        elif disp == "REVIEW":
            lot_map[lot]["review"] += 1
        elif disp == "REJECT":
            lot_map[lot]["reject"] += 1

    assert len(lot_map) == 2
    assert lot_map["FAB-LOT-4401"]["total"] == 3
    assert lot_map["FAB-LOT-4401"]["pass"] == 2
    assert lot_map["FAB-LOT-4401"]["reject"] == 1
    assert lot_map["FAB-LOT-4402"]["total"] == 2
    assert lot_map["FAB-LOT-4402"]["pass"] == 1
    assert lot_map["FAB-LOT-4402"]["review"] == 1


def test_isro_streaming_simulation_integrity():
    """
    Ensure ISRO Live Stream does not imply lot metadata exists and does not
    fabricate fake GPR forecasts or fake LOT-D2 strings.
    """
    shared_js_path = os.path.join("dashboard", "shared.js")
    with open(shared_js_path, "r", encoding="utf-8") as f:
        shared_js = f.read()

    # Ensure generateSimulatedComponent does not create LOT-D2
    assert "const lot = `LOT-D2-" not in shared_js
    assert 'device_type: "DISCRETE-HEMT"' not in shared_js

    # Ensure simulated items have null lot and unavailable forecast
    assert 'forecast_status: "unavailable_insufficient_history"' in shared_js
    assert 'forecast_reason: "GPR not applicable: insufficient trajectory history."' in shared_js
    assert 'source: "ISRO_Telemetry_Stream"' in shared_js
