"""
NASA Power Semiconductor Thermal Aging Dataset Intake & Canonical Mapping
========================================================================
Parses the 7 authentic NASA aging .mat files:
  Device2, Device2b, Device3, Device3b, Device4, Device4b, Device5

Maps to Canonical Schema adhering to Sections 11, 16, and 25 of the Implementation Guide:
  - component_id: Device ID (e.g. Device2, Device3b)
  - checkpoint: Standard screening checkpoint (0h, 12h, 24h, 48h, 72h, 96h, 120h, 144h, 168h)
  - elapsed_time: Cumulative elapsed hours mapped proportionally from cycle count
  - cycle_index: Actual raw steady-state cycle count
  - param_01: Collector-Emitter Current (A) - Primary degradation signal
  - param_02: Package Temperature (°C)
  - param_03: Heat Sink Temperature (°C)
  - param_04: Supply Voltage (V)
  - param_05: Node 1 Voltage (V)
"""

import os
import glob
import scipy.io as sio
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Tuple


class NasaMatAdapter:
    """Intake adapter for NASA Power Semiconductor degradation .mat files."""

    STANDARD_CHECKPOINTS = [0.0, 12.0, 24.0, 48.0, 72.0, 96.0, 120.0, 144.0, 168.0]

    def __init__(self, target_hours: float = 168.0):
        self.target_hours = target_hours

    def process_all_devices(self, data_dir: str = ".") -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Reads all NASA .mat files in data_dir, extracts raw and canonical checkpoint data.
        Returns: (raw_records_df, canonical_checkpoints_df)
        """
        mat_files = sorted(glob.glob(os.path.join(data_dir, "Device*.mat")))
        if not mat_files:
            raise FileNotFoundError(f"No Device*.mat files found in directory: {data_dir}")

        all_raw_rows = []
        canonical_rows = []

        for fpath in mat_files:
            fname = os.path.basename(fpath)
            dev_id = fname.split()[0].replace(".mat", "")

            mat = sio.loadmat(fpath, squeeze_me=True, struct_as_record=False)
            m = mat["measurement"]
            ss = m.steadyState
            n_records = len(ss)

            device_raw = []
            for idx in range(n_records):
                item = ss[idx]
                td = getattr(item, "timeDomain", None)
                if td is None:
                    continue

                curr = getattr(td, "collectorEmitterCurrent", np.nan)
                if np.isnan(curr) or curr <= 0:
                    continue

                pkg_temp = getattr(td, "packageTemperature", np.nan)
                hs_temp = getattr(td, "heatSinkTemperature", np.nan)
                sup_volt = getattr(td, "supplyVoltage", np.nan)
                node1_v = getattr(td, "node1Voltage", np.nan)
                epoch = getattr(item, "timeEpoch", np.nan)

                row = {
                    "component_id": dev_id,
                    "cycle_index": idx + 1,
                    "time_epoch": epoch,
                    "collector_current": float(curr),
                    "package_temp": float(pkg_temp) if not np.isnan(pkg_temp) else 0.0,
                    "heatsink_temp": float(hs_temp) if not np.isnan(hs_temp) else 0.0,
                    "supply_volt": float(sup_volt) if not np.isnan(sup_volt) else 0.0,
                    "node1_volt": float(node1_v) if not np.isnan(node1_v) else 0.0
                }
                device_raw.append(row)

            dev_df = pd.DataFrame(device_raw)
            if dev_df.empty:
                continue

            all_raw_rows.extend(device_raw)

            # Map proportional cycles to standard 168-hour burn-in checkpoints
            max_cycle = dev_df["cycle_index"].max()
            for cp in self.STANDARD_CHECKPOINTS:
                pct = cp / self.target_hours
                target_cycle = max(1, int(pct * max_cycle))
                # Window of +/- 50 cycles to smooth momentary sensor noise
                window_df = dev_df[
                    (dev_df["cycle_index"] >= max(1, target_cycle - 50)) &
                    (dev_df["cycle_index"] <= min(max_cycle, target_cycle + 50))
                ]
                if window_df.empty:
                    window_df = dev_df.iloc[[min(target_cycle, len(dev_df) - 1)]]

                canonical_rows.append({
                    "component_id": dev_id,
                    "part_type": "IGBT_Power_MOSFET",
                    "part_number": "IRG4BC30KD",
                    "lot_id": "NASA_PCoE_LOT1",
                    "checkpoint": float(cp),
                    "elapsed_time": float(cp),
                    "raw_cycle": int(target_cycle),
                    "param_01": round(float(window_df["collector_current"].mean()), 5),
                    "param_02": round(float(window_df["package_temp"].mean()), 3),
                    "param_03": round(float(window_df["heatsink_temp"].mean()), 3),
                    "param_04": round(float(window_df["supply_volt"].mean()), 4),
                    "param_05": round(float(window_df["node1_volt"].mean()), 4)
                })

        raw_df = pd.DataFrame(all_raw_rows)
        canonical_df = pd.DataFrame(canonical_rows)
        return raw_df, canonical_df


def extract_and_save_nasa_data():
    adapter = NasaMatAdapter()
    print("Extracting NASA degradation datasets...")
    raw_df, canonical_df = adapter.process_all_devices(".")
    
    os.makedirs("data/canonical", exist_ok=True)
    canonical_path = "data/canonical/NASA_degradation_canonical.csv"
    canonical_df.to_csv(canonical_path, index=False)
    print(f"Saved canonical screening dataset ({len(canonical_df)} records) to: {canonical_path}")
    print("\nSample Canonical Checkpoint Records:")
    print(canonical_df.head(10).to_string(index=False))

    # Also save full raw table for traceability
    raw_path = "data/NASA_steadyState_raw.csv"
    raw_df.to_csv(raw_path, index=False)
    print(f"Saved complete raw dataset ({len(raw_df):,} records) to: {raw_path}")
    return canonical_df

if __name__ == "__main__":
    extract_and_save_nasa_data()
