"""
NASA Power Semiconductor Thermal Aging Dataset Intake & Canonical Mapping
========================================================================
Parses the 7 authentic NASA aging .mat files:
  Device2, Device2b, Device3, Device3b, Device4, Device4b, Device5

Correct Physical-Device Grouping (Preserving Hardware Boundaries):
  - Physical Device 2: Device2  1.mat + Device2b  1.mat (sequential test run, 165s pause)
  - Physical Device 3: Device3  1.mat + Device3b  1.mat (sequential test run, 41s pause)
  - Physical Device 4: Device4  1.mat + Device4b  1.mat (sequential test run, 838s pause)
  - Physical Device 5: Device5  1.mat (single continuous run)

Maps to Canonical Schema adhering to Sections 11, 16, 20, and 25 of the Implementation Guide:
  - component_id: Physical Device ID (Device_2, Device_3, Device_4, Device_5)
  - physical_device_id: Physical Device identifier for strict physical-device split validation
  - source_files: Traceable constituent raw .mat files
  - checkpoint: Standard screening checkpoint (0h, 12h, 24h, 48h, 72h, 96h, 120h, 144h, 168h)
  - elapsed_time: Cumulative elapsed hours mapped proportionally from physical lifetime cycle count
  - raw_cycle: Unified cumulative cycle index across continued test runs
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
    """Intake adapter for NASA Power Semiconductor degradation .mat files with physical device grouping."""

    STANDARD_CHECKPOINTS = [0.0, 12.0, 24.0, 48.0, 72.0, 96.0, 120.0, 144.0, 168.0]

    # Authentic Physical Device Grouping verified from experiment timeEpochs and reports
    PHYSICAL_DEVICE_GROUPS = {
        "Device_2": ["Device2  1.mat", "Device2b  1.mat"],
        "Device_3": ["Device3  1.mat", "Device3b  1.mat"],
        "Device_4": ["Device4  1.mat", "Device4b  1.mat"],
        "Device_5": ["Device5  1.mat"]
    }

    def __init__(self, target_hours: float = 168.0):
        self.target_hours = target_hours

    @classmethod
    def get_physical_device_mapping(cls) -> Dict[str, str]:
        """Returns map from raw file prefix to physical device identifier."""
        return {
            "Device2": "Device_2",
            "Device2b": "Device_2",
            "Device3": "Device_3",
            "Device3b": "Device_3",
            "Device4": "Device_4",
            "Device4b": "Device_4",
            "Device5": "Device_5",
        }

    def _find_mat_file(self, filename: str, search_dirs: List[str]) -> str:
        for sdir in search_dirs:
            candidate = os.path.join(sdir, filename)
            if os.path.exists(candidate):
                return candidate
            # Try glob in case spacing differs
            prefix = filename.split()[0].replace(".mat", "")
            matches = glob.glob(os.path.join(sdir, f"{prefix}*.mat"))
            if matches:
                return matches[0]
        raise FileNotFoundError(f"Could not find NASA MAT file '{filename}' in search dirs: {search_dirs}")

    def process_all_devices(self, data_dir: str = ".") -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Reads all 7 NASA .mat files, groups base and base-b into unified physical devices,
        and extracts canonical checkpoint data.

        Returns: (raw_records_df, canonical_checkpoints_df)
        """
        search_dirs = [
            data_dir,
            os.path.join(data_dir, "data", "raw"),
            os.path.join(data_dir, "raw"),
            "data/raw",
            "."
        ]

        all_raw_rows = []
        canonical_rows = []

        for phys_id, file_list in self.PHYSICAL_DEVICE_GROUPS.items():
            phys_device_raw = []
            cycle_offset = 0

            for fname in file_list:
                fpath = self._find_mat_file(fname, search_dirs)
                dev_sub_id = os.path.basename(fpath).split()[0].replace(".mat", "")

                mat = sio.loadmat(fpath, squeeze_me=True, struct_as_record=False)
                m = mat["measurement"]
                ss = m.steadyState
                n_records = len(ss)

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
                        "physical_device_id": phys_id,
                        "component_id": phys_id,
                        "sub_device_id": dev_sub_id,
                        "source_file": os.path.basename(fpath),
                        "cycle_index": cycle_offset + idx + 1,
                        "local_cycle": idx + 1,
                        "time_epoch": epoch,
                        "collector_current": float(curr),
                        "package_temp": float(pkg_temp) if not np.isnan(pkg_temp) else 0.0,
                        "heatsink_temp": float(hs_temp) if not np.isnan(hs_temp) else 0.0,
                        "supply_volt": float(sup_volt) if not np.isnan(sup_volt) else 0.0,
                        "node1_volt": float(node1_v) if not np.isnan(node1_v) else 0.0
                    }
                    phys_device_raw.append(row)

                cycle_offset += n_records

            dev_df = pd.DataFrame(phys_device_raw)
            if dev_df.empty:
                continue

            all_raw_rows.extend(phys_device_raw)

            # Map unified physical device cycles to standard 168-hour burn-in checkpoints
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
                    "component_id": phys_id,
                    "physical_device_id": phys_id,
                    "source_files": ", ".join([f.split()[0] for f in file_list]),
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


def extract_and_save_nasa_data(output_dir: str = "data"):
    adapter = NasaMatAdapter()
    print("Extracting NASA degradation datasets with physical device grouping...")
    raw_df, canonical_df = adapter.process_all_devices("data/raw")

    os.makedirs(os.path.join(output_dir, "canonical"), exist_ok=True)
    canonical_path = os.path.join(output_dir, "canonical", "NASA_degradation_canonical.csv")
    canonical_df.to_csv(canonical_path, index=False)
    print(f"Saved canonical screening dataset ({len(canonical_df)} records, {canonical_df['component_id'].nunique()} physical devices) to: {canonical_path}")

    # Also save to data/NASA.csv for direct intake
    nasa_csv_path = os.path.join(output_dir, "NASA.csv")
    canonical_df.to_csv(nasa_csv_path, index=False)
    print(f"Saved canonical dataset to: {nasa_csv_path}")

    # Also save full raw table for traceability
    raw_path = os.path.join(output_dir, "NASA_steadyState_raw.csv")
    raw_df.to_csv(raw_path, index=False)
    print(f"Saved complete raw dataset ({len(raw_df):,} records across 4 physical devices) to: {raw_path}")

    print("\nCanonical Physical Devices Summary:")
    print(canonical_df.groupby("component_id")[["checkpoint", "param_01"]].agg({"checkpoint": "count", "param_01": ["first", "last"]}))
    return canonical_df


if __name__ == "__main__":
    extract_and_save_nasa_data()
