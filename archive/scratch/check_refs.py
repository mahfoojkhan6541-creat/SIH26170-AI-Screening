import os
import re

files_to_check = []
for root, dirs, files in os.walk('.'):
    if any(skip in root for skip in ['.git', 'venv', 'node_modules', '.pytest_cache']):
        continue
    for f in files:
        if f.endswith(('.py', '.yaml', '.json', '.bat', '.sh', '.ts', '.tsx', '.js', '.html')):
            files_to_check.append(os.path.join(root, f))

print(f"Total code/config files to search through: {len(files_to_check)}")

final_backup_refs = []
features_refs = []
scratch_refs = []
numbered_script_refs = []

for fpath in files_to_check:
    try:
        with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            if 'final_backup' in content:
                final_backup_refs.append(fpath)
            if 'features/' in content or 'features\\' in content or 'features"' in content or "'features'" in content:
                # exclude files inside features itself
                if not fpath.startswith('.\\features') and not fpath.startswith('./features'):
                    features_refs.append(fpath)
            if 'scratch/' in content or 'scratch\\' in content:
                if not fpath.startswith('.\\scratch') and not fpath.startswith('./scratch'):
                    scratch_refs.append(fpath)
            matches = re.findall(r'\b[0-6][0-9]_[a-zA-Z0-9_]+\.py\b', content)
            if matches:
                base = os.path.basename(fpath)
                ext_m = [x for x in matches if x != base]
                if ext_m:
                    numbered_script_refs.append((fpath, ext_m))
    except Exception as e:
        print(f"Error reading {fpath}: {e}")

print("\n--- References to final_backup ---")
for r in final_backup_refs:
    print(" ", r)

print("\n--- References to features/ folder outside features ---")
for r in features_refs:
    print(" ", r)

print("\n--- References to scratch/ folder outside scratch ---")
for r in scratch_refs:
    print(" ", r)

print("\n--- References to numbered scripts [0-6][0-9]_*.py outside themselves ---")
for r, m in numbered_script_refs:
    print(f"  {r} -> {m}")
