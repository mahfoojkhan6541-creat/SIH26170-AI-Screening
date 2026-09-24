"""
Profile NASA MAT degradation records:
- Check non-NaN valid rows per device
- Examine time/cycle ranges
- Check drift of parameters (collectorEmitterCurrent, packageTemperature, etc.)
- Select the best degradation forecast target
"""

import os
import glob
import scipy.io as sio
import numpy as np
import pandas as pd

def profile_device_measurements():
    mat_files = sorted(glob.glob("data/raw/Device*.mat") + glob.glob("Device*.mat"))
    print(f"Profiling {len(mat_files)} NASA device files...\n")
    
    device_dfs = {}
    
    for fpath in mat_files:
        fname = os.path.basename(fpath)
        dev_id = fname.split()[0].replace(".mat", "")
        print(f"Reading {dev_id} from {fname}...")
        
        mat = sio.loadmat(fpath, squeeze_me=True, struct_as_record=False)
        m = mat["measurement"]
        ss = m.steadyState
        n_records = len(ss)
        
        rows = []
        for idx in range(n_records):
            item = ss[idx]
            td = getattr(item, "timeDomain", None)
            if td is None:
                continue
                
            epoch = getattr(item, "timeEpoch", np.nan)
            date_str = str(getattr(item, "date", ""))
            
            row = {
                "device_id": dev_id,
                "cycle": idx + 1,
                "time_epoch": epoch,
                "date": date_str,
                "ambient_temp": getattr(td, "ambientTemperature", np.nan),
                "collector_current": getattr(td, "collectorEmitterCurrent", np.nan),
                "heatsink_temp": getattr(td, "heatSinkTemperature", np.nan),
                "internal_temp": getattr(td, "internalTemperature", np.nan),
                "node1_volt": getattr(td, "node1Voltage", np.nan),
                "node2_volt": getattr(td, "node2Voltage", np.nan),
                "package_temp": getattr(td, "packageTemperature", np.nan),
                "supply_volt": getattr(td, "supplyVoltage", np.nan)
            }
            rows.append(row)
            
        df = pd.DataFrame(rows)
        # Drop rows where all signals are NaN or epoch is 0
        valid_df = df[df["collector_current"].notnull() & (df["collector_current"] > 0)]
        print(f"  Total records: {len(df):,}, Valid non-null records: {len(valid_df):,}")
        if not valid_df.empty:
            print(f"  Cycle range: {valid_df['cycle'].min()} to {valid_df['cycle'].max()}")
            print(f"  Collector Current: min={valid_df['collector_current'].min():.4f}, mean={valid_df['collector_current'].mean():.4f}, max={valid_df['collector_current'].max():.4f}")
            print(f"  Package Temp: min={valid_df['package_temp'].min():.2f}, mean={valid_df['package_temp'].mean():.2f}, max={valid_df['package_temp'].max():.2f}")
            print(f"  Supply Volt: min={valid_df['supply_volt'].min():.4f}, max={valid_df['supply_volt'].max():.4f}")
            
            # Check drift between first 100 cycles and last 100 cycles
            early_curr = valid_df.head(100)["collector_current"].mean()
            late_curr = valid_df.tail(100)["collector_current"].mean()
            drift_pct = ((late_curr - early_curr) / early_curr) * 100
            print(f"  Current Drift (early 100 vs late 100): {early_curr:.4f} -> {late_curr:.4f} ({drift_pct:+.2f}%)")
            
        device_dfs[dev_id] = valid_df
        print("-" * 60)
        
    return device_dfs

if __name__ == "__main__":
    profile_device_measurements()
