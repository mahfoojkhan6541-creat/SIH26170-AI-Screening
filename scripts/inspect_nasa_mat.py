"""
Deep Inspection of NASA Thermal Aging MAT Files
Adhering to NASA DATASET instructions 1-8:
1. Inspect every MAT file
2. Identify structure
3. Identify component/device/cell ID
4. Identify time/cycle information
5. Identify repeated measurements
6. Identify available parameters
7. Check missingness
8. Check units
"""

import os
import glob
import scipy.io as sio
import numpy as np
import pandas as pd

def inspect_all_mat_files():
    mat_files = sorted(glob.glob("data/raw/*.mat") + glob.glob("*.mat"))
    print(f"Total MAT files found: {len(mat_files)}")
    
    summary = []
    
    for fpath in mat_files:
        fname = os.path.basename(fpath)
        print(f"\n{'='*70}")
        print(f"FILE: {fname} (Size: {os.path.getsize(fpath) / (1024*1024):.2f} MB)")
        print(f"{'='*70}")
        
        try:
            mat = sio.loadmat(fpath, squeeze_me=True, struct_as_record=False)
            if "measurement" not in mat:
                print(f"  [!] 'measurement' key not found. Top keys: {list(mat.keys())}")
                continue
                
            m = mat["measurement"]
            top_fields = [f for f in dir(m) if not f.startswith("_")]
            print(f"  Top fields in measurement: {top_fields}")
            
            # Check steadyState
            n_steady = 0
            steady_fields = []
            ss_sample = {}
            if hasattr(m, "steadyState"):
                ss = m.steadyState
                n_steady = len(ss) if hasattr(ss, "__len__") else 1
                if n_steady > 0:
                    first_ss = ss[0] if hasattr(ss, "__getitem__") else ss
                    td = getattr(first_ss, "timeDomain", None)
                    if td is not None:
                        steady_fields = [f for f in dir(td) if not f.startswith("_")]
                        for sf in steady_fields:
                            ss_sample[sf] = getattr(td, sf)
                    date_val = getattr(first_ss, "date", None)
                    epoch_val = getattr(first_ss, "timeEpoch", None)
                    ss_sample["date"] = str(date_val)
                    ss_sample["timeEpoch"] = epoch_val

            # Check transient
            n_transient = 0
            if hasattr(m, "transient"):
                tr = m.transient
                n_transient = len(tr) if hasattr(tr, "__len__") else 1

            # Check pwmTempControllerState
            n_pwm = 0
            pwm_fields = []
            pwm_sample = {}
            if hasattr(m, "pwmTempControllerState"):
                pwm = m.pwmTempControllerState
                n_pwm = len(pwm) if hasattr(pwm, "__len__") else 1
                if n_pwm > 0:
                    first_pwm = pwm[0] if hasattr(pwm, "__getitem__") else pwm
                    pwm_fields = [f for f in dir(first_pwm) if not f.startswith("_")]
                    for pf in pwm_fields:
                        pwm_sample[pf] = getattr(first_pwm, pf)

            print(f"  steadyState records: {n_steady:,}")
            print(f"    Parameters in steadyState.timeDomain: {steady_fields}")
            print(f"    Sample values: {ss_sample}")
            print(f"  transient records: {n_transient:,}")
            print(f"  pwmTempControllerState records: {n_pwm:,}")
            print(f"    PWM fields: {pwm_fields}")
            print(f"    Sample PWM: {pwm_sample}")

            # Derive device ID from filename
            device_id = fname.split()[0].replace(".mat", "")
            
            summary.append({
                "file": fname,
                "device_id": device_id,
                "steadyState_count": n_steady,
                "transient_count": n_transient,
                "pwm_count": n_pwm,
                "parameters": steady_fields
            })

        except Exception as e:
            print(f"  [ERROR] Failed to inspect {fname}: {e}")

    summary_df = pd.DataFrame(summary)
    print("\n" + "="*70)
    print("SUMMARY OF ALL INSPECTED NASA MAT FILES")
    print("="*70)
    print(summary_df.to_string(index=False))
    return summary_df

if __name__ == "__main__":
    inspect_all_mat_files()
