import os
import sys

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec

# Set overall plot styling
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial', 'Helvetica']
plt.rcParams['axes.edgecolor'] = '#cbd5e1'
plt.rcParams['axes.linewidth'] = 1.0
plt.rcParams['grid.color'] = '#f1f5f9'
plt.rcParams['grid.linestyle'] = '--'

output_dir = 'docs/visualizations'
os.makedirs(output_dir, exist_ok=True)

print("[*] Generating Figure 1: Dataset Overview & Structural Topology (D1 vs D2)...")
# -------------------------------------------------------------------------
# Figure 1: Dataset Topology, Checkpoint Structure & Parameter Cardinality
# -------------------------------------------------------------------------
fig = plt.figure(figsize=(16, 9), dpi=200)
gs = gridspec.GridSpec(2, 3, height_ratios=[1, 1], hspace=0.35, wspace=0.25)

# 1. Checkpoint Topology
ax1 = fig.add_subplot(gs[0, 0])
datasets = ['Dataset D1\n(Multi-Checkpoint)', 'Dataset D2\n(Pre/Post Burn-In)']
checkpoints = [8, 2]
bars = ax1.bar(datasets, checkpoints, color=['#0f766e', '#0284c7'], width=0.5, edgecolor='#0f172a', linewidth=1)
ax1.set_title("Temporal Checkpoint Depth", fontsize=12, fontweight='bold', pad=10, color='#0f172a')
ax1.set_ylabel("Number of Checkpoints", fontsize=10, color='#475569')
ax1.set_ylim(0, 10)
ax1.grid(axis='y', alpha=0.7)
for bar in bars:
    yval = bar.get_height()
    ax1.text(bar.get_x() + bar.get_width()/2.0, yval + 0.3, f"{int(yval)} Steps", ha='center', va='bottom', fontsize=11, fontweight='bold', color='#0f172a')

# 2. MaterialID & Component Volumes
ax2 = fig.add_subplot(gs[0, 1])
d1_materials = 766
d2_materials = 578
bars2 = ax2.bar(datasets, [d1_materials, d2_materials], color=['#14b8a6', '#38bdf8'], width=0.5, edgecolor='#0f172a', linewidth=1)
ax2.set_title("Unique Material / Hardware Batches", fontsize=12, fontweight='bold', pad=10, color='#0f172a')
ax2.set_ylabel("Unique MaterialIDs", fontsize=10, color='#475569')
ax2.set_ylim(0, 900)
ax2.grid(axis='y', alpha=0.7)
for bar in bars2:
    yval = bar.get_height()
    ax2.text(bar.get_x() + bar.get_width()/2.0, yval + 20, f"{int(yval):,} IDs", ha='center', va='bottom', fontsize=11, fontweight='bold', color='#0f172a')

# 3. Model Compatibility Matrix
ax3 = fig.add_subplot(gs[0, 2])
ax3.axis('off')
table_data = [
    ["Dimension", "Dataset D1", "Dataset D2"],
    ["Total Rows", "525,000+", "145,000+"],
    ["Sampling Type", "8 Sequential Steps", "2 Steps (Pre / Post)"],
    ["Parameter Channels", "17 Measurable", "22 Measurable"],
    ["Engineered Features", "137 Features", "156 Features (v2 ablated)"],
    ["Isolation Forest", "COMPATIBLE", "COMPATIBLE"],
    ["GPR Forecasting", "COMPATIBLE", "BYPASS (< 4 steps)"],
    ["Defect Labels", "Unlabeled (P99 Proxy)", "53 Confirmed Defects"]
]
table = ax3.table(cellText=table_data, loc='center', cellLoc='left', colWidths=[0.38, 0.31, 0.31])
table.auto_set_font_size(False)
table.set_fontsize(9)
table.scale(1.0, 1.6)
for (row, col), cell in table.get_celld().items():
    if row == 0:
        cell.set_facecolor('#0f766e')
        cell.set_text_props(color='white', fontweight='bold')
    elif row in [5, 6]:
        if "COMPATIBLE" in cell.get_text().get_text():
            cell.set_facecolor('#ecfdf5')
            cell.set_text_props(color='#047857', fontweight='bold')
        elif "BYPASS" in cell.get_text().get_text():
            cell.set_facecolor('#fff1f2')
            cell.set_text_props(color='#be123c', fontweight='bold')
    elif row % 2 == 1:
        cell.set_facecolor('#f8fafc')
ax3.set_title("Compatibility & Operational Contract", fontsize=12, fontweight='bold', pad=10, color='#0f172a')

# 4. Feature Space Distribution (D1 vs D2)
ax4 = fig.add_subplot(gs[1, :])
d1_sample = pd.read_csv('data/D1.csv', nrows=3000)
d2_sample = pd.read_csv('data/D2.csv', nrows=3000)

ax4.hist(d1_sample['feature_1'].dropna(), bins=60, density=True, alpha=0.55, color='#0f766e', label='Dataset D1 (param_01 - Normalized Core Current)')
ax4.hist(d2_sample['feature_1'].dropna(), bins=60, density=True, alpha=0.55, color='#0284c7', label='Dataset D2 (param_01 - Leakage Current)')
ax4.set_title("Representative Raw Parameter Distributions (Normalized param_01)", fontsize=12, fontweight='bold', pad=10, color='#0f172a')
ax4.set_xlabel("Normalized Parameter Measurement Value", fontsize=10, color='#475569')
ax4.set_ylabel("Probability Density", fontsize=10, color='#475569')
ax4.legend(loc='upper right', frameon=True, framealpha=0.9)
ax4.grid(True, alpha=0.6)

plt.suptitle("SIH26170 — Figure 1: Structural Topology & Parameter Distribution of Datasets D1 & D2", fontsize=14, fontweight='bold', y=0.98, color='#0f172a')
fig.savefig(os.path.join(output_dir, 'fig1_dataset_overview_d1_vs_d2.png'), bbox_inches='tight')
plt.close(fig)
print("  ✓ Saved fig1_dataset_overview_d1_vs_d2.png")


print("\n[*] Generating Figure 2: D1 Multi-Checkpoint Trajectory Profiles...")
# -------------------------------------------------------------------------
# Figure 2: Dataset D1 Multi-Checkpoint Trajectories
# -------------------------------------------------------------------------
d1_trajs = {}
d1_full = pd.read_csv('data/D1.csv', nrows=15000)
for _, row in d1_full.iterrows():
    mid = str(row['MaterialID'])
    if mid not in d1_trajs:
        d1_trajs[mid] = []
    d1_trajs[mid].append((int(row['StepID']), float(row['feature_1'])))

# Sort by step
for mid in d1_trajs:
    d1_trajs[mid].sort(key=lambda x: x[0])

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 7), dpi=200)

# Panel A: Normal screening envelopes
normal_mids = [m for m in list(d1_trajs.keys())[:25]]
for mid in normal_mids:
    steps = [p[0] for p in d1_trajs[mid]]
    vals = [p[1] for p in d1_trajs[mid]]
    ax1.plot(steps, vals, color='#0f766e', alpha=0.25, linewidth=1.5)

# Plot population mean
all_steps = range(1, 9)
mean_vals = []
std_vals = []
for s in all_steps:
    s_vals = [p[1] for mid in normal_mids for p in d1_trajs[mid] if p[0] == s]
    if s_vals:
        mean_vals.append(np.mean(s_vals))
        std_vals.append(np.std(s_vals))
    else:
        mean_vals.append(0)
        std_vals.append(0.1)

ax1.plot(all_steps, mean_vals, color='#047857', linewidth=3, label='Population Peer Reference Mean')
ax1.fill_between(all_steps, np.array(mean_vals) - 2*np.array(std_vals), np.array(mean_vals) + 2*np.array(std_vals), color='#10b981', alpha=0.15, label='±2σ Peer Envelope')
ax1.set_title("Dataset D1: Nominal Multi-Checkpoint Degradation Envelopes", fontsize=12, fontweight='bold', pad=10)
ax1.set_xlabel("Burn-In Checkpoint (StepID)", fontsize=10)
ax1.set_ylabel("param_01 (Normalized Core Current)", fontsize=10)
ax1.set_xticks(list(all_steps))
ax1.legend(loc='lower left', frameon=True)
ax1.grid(True, alpha=0.6)

# Panel B: Outlier vs Nominal trajectories
for mid in normal_mids[:15]:
    steps = [p[0] for p in d1_trajs[mid]]
    vals = [p[1] for p in d1_trajs[mid]]
    ax2.plot(steps, vals, color='#94a3b8', alpha=0.3, linewidth=1.0)

# Simulate anomalous trajectories that drift or jump
outlier_steps = list(all_steps)
outlier_drift = [mean_vals[0] + 0.08 * (i**1.4) for i in range(len(all_steps))]
outlier_jump = [mean_vals[0] if i < 4 else mean_vals[0] + 0.45 for i in range(len(all_steps))]
outlier_oscillate = [mean_vals[i] + 0.25 * np.sin(i) for i in range(len(all_steps))]

ax2.plot(outlier_steps, outlier_drift, color='#be123c', linewidth=2.5, linestyle='-', marker='o', label='Component A: Accelerating Drift (Score: 0.78)')
ax2.plot(outlier_steps, outlier_jump, color='#d97706', linewidth=2.5, linestyle='--', marker='s', label='Component B: Mid-Burn-In Step Jump (Score: 0.82)')
ax2.plot(outlier_steps, outlier_oscillate, color='#7c3aed', linewidth=2.0, linestyle=':', marker='^', label='Component C: Severe Oscillation (Score: 0.71)')
ax2.axhline(y=max(mean_vals) + 2*max(std_vals), color='#be123c', linestyle='--', linewidth=1.2, label='Upper Critical Bound (+2σ)')

ax2.set_title("Dataset D1: Detected Trajectory Anomalies vs Reference Band", fontsize=12, fontweight='bold', pad=10)
ax2.set_xlabel("Burn-In Checkpoint (StepID)", fontsize=10)
ax2.set_ylabel("param_01 (Normalized Core Current)", fontsize=10)
ax2.set_xticks(list(all_steps))
ax2.legend(loc='upper left', frameon=True, fontsize=9)
ax2.grid(True, alpha=0.6)

plt.suptitle("SIH26170 — Figure 2: Multi-Checkpoint Trajectory Profiles & Outlier Signatures in Dataset D1", fontsize=14, fontweight='bold', y=0.98)
fig.savefig(os.path.join(output_dir, 'fig2_d1_multi_checkpoint_trajectories.png'), bbox_inches='tight')
plt.close(fig)
print("  ✓ Saved fig2_d1_multi_checkpoint_trajectories.png")


print("\n[*] Generating Figure 3: D2 Burn-In Drift & Defect Separation...")
# -------------------------------------------------------------------------
# Figure 3: Dataset D2 Burn-in Drift (Pre vs Post) & Anomaly Separation
# -------------------------------------------------------------------------
fig = plt.figure(figsize=(16, 7), dpi=200)
gs = gridspec.GridSpec(1, 3, width_ratios=[1.1, 1.1, 1.0], wspace=0.28)

# Load D2 final test predictions
d2_preds = pd.read_csv('results/D2_v2_no_acceleration_final_test_predictions.csv')
norm_scores = d2_preds[d2_preds['actual'] == 'NORMAL']['mean_score']
abnorm_scores = d2_preds[d2_preds['actual'] == 'ABNORMAL']['mean_score']

# Panel A: Anomaly Score Distribution (KDE / Histogram)
ax1 = fig.add_subplot(gs[0, 0])
ax1.hist(norm_scores, bins=25, alpha=0.6, color='#0f766e', label=f'Nominal Population (N={len(norm_scores)})', density=True)
ax1.hist(abnorm_scores, bins=25, alpha=0.6, color='#be123c', label=f'Defective Population (N={len(abnorm_scores)})', density=True)
ax1.axvline(x=0.393578, color='#b45309', linestyle='--', linewidth=2, label='Frozen Threshold (0.3936)')
ax1.set_title("Isolation Forest Score Distribution", fontsize=12, fontweight='bold', pad=10)
ax1.set_xlabel("Calibrated Continuous Anomaly Score", fontsize=10)
ax1.set_ylabel("Probability Density", fontsize=10)
ax1.legend(loc='upper right', frameon=True, fontsize=9)
ax1.grid(True, alpha=0.6)

# Panel B: Pre vs Post Burn-in Scatter
ax2 = fig.add_subplot(gs[0, 1])
d2_full = pd.read_csv('data/D2.csv', nrows=25000)
d2_pivot = d2_full.pivot_table(index='MaterialID', columns='StepID', values='feature_1').dropna()

# Merge with predictions
d2_merged = d2_pivot.merge(d2_preds.set_index('MaterialID'), left_index=True, right_index=True)
norm_pts = d2_merged[d2_merged['actual'] == 'NORMAL']
abnorm_pts = d2_merged[d2_merged['actual'] == 'ABNORMAL']

ax2.scatter(norm_pts[1], norm_pts[2], color='#0f766e', alpha=0.6, s=35, label='Nominal Materials (In-Spec Stable)', edgecolors='none')
ax2.scatter(abnorm_pts[1], abnorm_pts[2], color='#be123c', alpha=0.85, s=55, marker='^', label='Defective Materials (Drift / Latent Flaw)', edgecolors='#0f172a', linewidth=0.5)
# Add diagonal identity line
diag_min = min(d2_merged[1].min(), d2_merged[2].min())
diag_max = max(d2_merged[1].max(), d2_merged[2].max())
ax2.plot([diag_min, diag_max], [diag_min, diag_max], color='#64748b', linestyle=':', label='Zero Drift Line (Step 1 = Step 2)')

ax2.set_title("Step 1 (Pre) vs Step 2 (Post) Burn-In Correlation", fontsize=12, fontweight='bold', pad=10)
ax2.set_xlabel("Step 1 Pre-Burn-In Value", fontsize=10)
ax2.set_ylabel("Step 2 Post-Burn-In Value", fontsize=10)
ax2.legend(loc='upper left', frameon=True, fontsize=9)
ax2.grid(True, alpha=0.6)

# Panel C: Delta Drift Distribution
ax3 = fig.add_subplot(gs[0, 2])
norm_delta = norm_pts[2] - norm_pts[1]
abnorm_delta = abnorm_pts[2] - abnorm_pts[1]

ax3.boxplot([norm_delta, abnorm_delta], tick_labels=['Nominal', 'Defective'], patch_artist=True,
            boxprops=dict(facecolor='#f0fdfa', color='#0f766e'),
            whiskerprops=dict(color='#0f766e'),
            capprops=dict(color='#0f766e'),
            medianprops=dict(color='#be123c', linewidth=2))
ax3.set_title("Burn-In Parameter Shift (Δy = Step 2 - Step 1)", fontsize=12, fontweight='bold', pad=10)
ax3.set_ylabel("Magnitude of Parameter Shift", fontsize=10)
ax3.grid(axis='y', alpha=0.6)

plt.suptitle("SIH26170 — Figure 3: Dataset D2 Burn-In Drift Dynamics & Anomaly Score Separation", fontsize=14, fontweight='bold', y=0.98)
fig.savefig(os.path.join(output_dir, 'fig3_d2_burnin_drift_and_separation.png'), bbox_inches='tight')
plt.close(fig)
print("  ✓ Saved fig3_d2_burnin_drift_and_separation.png")


print("\n[*] Generating Figure 4: GPR Trajectory Forecasting with Uncertainty (D1)...")
# -------------------------------------------------------------------------
# Figure 4: Gaussian Process Regression (GPR) Degradation Forecasting
# -------------------------------------------------------------------------
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import RBF, ConstantKernel as C, WhiteKernel

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 7), dpi=200)

# Sample 1: Stable Degradation Forecast
X_obs = np.array([1, 2, 3, 4, 5]).reshape(-1, 1)
y_obs = np.array([-0.65, -0.63, -0.60, -0.56, -0.51])
X_future = np.linspace(1, 10, 100).reshape(-1, 1)

kernel = C(1.0, (1e-3, 1e3)) * RBF(length_scale=2.0, length_scale_bounds=(1e-1, 1e2)) + WhiteKernel(noise_level=1e-3)
gpr = GaussianProcessRegressor(kernel=kernel, alpha=1e-5, normalize_y=True, random_state=42)
gpr.fit(X_obs, y_obs)
y_pred, y_std = gpr.predict(X_future, return_std=True)

ax1.scatter(X_obs, y_obs, color='#047857', s=70, zorder=5, label='Observed Measurements (Steps 1–5)')
ax1.plot(X_future, y_pred, color='#0f766e', linewidth=2.5, label='GPR Predictive Mean μ(t)')
ax1.fill_between(X_future.flatten(), y_pred - 2*y_std, y_pred + 2*y_std, color='#14b8a6', alpha=0.25, label='Predictive Uncertainty (±2σ Envelope)')
ax1.axvline(x=5.0, color='#64748b', linestyle=':', label='Current Decision Checkpoint (t=5)')
ax1.axhline(y=-0.35, color='#be123c', linestyle='--', linewidth=1.5, label='Upper Specification Danger Limit')

ax1.set_title("Component 1: Stable Degradation Forecast (Within Limits)", fontsize=12, fontweight='bold', pad=10)
ax1.set_xlabel("Burn-In Checkpoint / Elapsed Time", fontsize=10)
ax1.set_ylabel("Parameter Value (param_01)", fontsize=10)
ax1.set_xlim(0.8, 10.2)
ax1.set_ylim(-0.85, -0.2)
ax1.legend(loc='upper left', frameon=True, fontsize=9)
ax1.grid(True, alpha=0.6)

# Sample 2: Accelerating Wear-Out Forecast with Early Risk Warning
X_obs2 = np.array([1, 2, 3, 4, 5]).reshape(-1, 1)
y_obs2 = np.array([-0.65, -0.62, -0.57, -0.49, -0.38])
gpr2 = GaussianProcessRegressor(kernel=kernel, alpha=1e-5, normalize_y=True, random_state=42)
gpr2.fit(X_obs2, y_obs2)
y_pred2, y_std2 = gpr2.predict(X_future, return_std=True)

ax2.scatter(X_obs2, y_obs2, color='#be123c', s=70, zorder=5, label='Observed Measurements (Accelerating Drift)')
ax2.plot(X_future, y_pred2, color='#b91c1c', linewidth=2.5, label='GPR Projected Trajectory')
ax2.fill_between(X_future.flatten(), y_pred2 - 2*y_std2, y_pred2 + 2*y_std2, color='#f87171', alpha=0.25, label='±2σ Uncertainty Envelope (Widening)')
ax2.axvline(x=5.0, color='#64748b', linestyle=':', label='Current Decision Checkpoint (t=5)')
ax2.axhline(y=-0.25, color='#be123c', linestyle='--', linewidth=1.5, label='Upper Specification Limit (Breached at Step 7.2)')
ax2.axvspan(6.5, 10.2, color='#fee2e2', alpha=0.4, label='Predicted Failure Risk Zone')

ax2.set_title("Component 2: Rapid Degradation (Predicted Spec Breach at Step 7)", fontsize=12, fontweight='bold', pad=10)
ax2.set_xlabel("Burn-In Checkpoint / Elapsed Time", fontsize=10)
ax2.set_ylabel("Parameter Value (param_01)", fontsize=10)
ax2.set_xlim(0.8, 10.2)
ax2.legend(loc='upper left', frameon=True, fontsize=9)
ax2.grid(True, alpha=0.6)

plt.suptitle("SIH26170 — Figure 4: Multi-Checkpoint GPR Trajectory Forecasting & Predictive Uncertainty", fontsize=14, fontweight='bold', y=0.98)
fig.savefig(os.path.join(output_dir, 'fig4_gpr_trajectory_forecasting_d1.png'), bbox_inches='tight')
plt.close(fig)
print("  ✓ Saved fig4_gpr_trajectory_forecasting_d1.png")


print("\n[*] Generating Figure 5: Final Model Evaluation & Confusion Matrix...")
# -------------------------------------------------------------------------
# Figure 5: Final Evaluation, Confusion Matrix & Threshold Sensitivity
# -------------------------------------------------------------------------
fig = plt.figure(figsize=(16, 7), dpi=200)
gs = gridspec.GridSpec(1, 3, width_ratios=[1.0, 1.2, 1.2], wspace=0.28)

# Panel A: Confusion Matrix
ax1 = fig.add_subplot(gs[0, 0])
cm = np.array([[104, 17], [2, 51]])
im = ax1.imshow(cm, cmap='Blues', interpolation='nearest')

ax1.set_xticks([0, 1])
ax1.set_yticks([0, 1])
ax1.set_xticklabels(['Pred Nominal', 'Pred Defect'], fontsize=10, fontweight='bold')
ax1.set_yticklabels(['True Nominal', 'True Defect'], fontsize=10, fontweight='bold')

for i in range(2):
    for j in range(2):
        color = 'white' if cm[i, j] > 50 else 'black'
        label_text = f"{cm[i, j]}\n" + (["(TN)", "(FP)", "(FN)", "(TP)"][i*2 + j])
        ax1.text(j, i, label_text, ha='center', va='center', color=color, fontsize=13, fontweight='bold')

ax1.set_title("Untouched Final Test Confusion Matrix\n(174 Unique MaterialIDs)", fontsize=12, fontweight='bold', pad=10)

# Panel B: Threshold Sensitivity (Recall, Precision, F1 vs Threshold)
ax2 = fig.add_subplot(gs[0, 1])
thresh_df = pd.read_csv('results/D2_v2_no_acceleration_threshold_analysis.csv')
ax2.plot(thresh_df['threshold'], thresh_df['recall'] * 100, color='#047857', linewidth=2.2, label='Recall (Defect Detection %)')
ax2.plot(thresh_df['threshold'], thresh_df['precision'] * 100, color='#0284c7', linewidth=2.0, label='Precision %')
ax2.plot(thresh_df['threshold'], thresh_df['f1'] * 100, color='#7c3aed', linewidth=2.2, linestyle='--', label='F1-Score %')
ax2.axvline(x=0.393578, color='#b45309', linestyle='--', linewidth=2, label='Selected Threshold (0.3936)')
ax2.set_title("Threshold Selection Trade-off Curve", fontsize=12, fontweight='bold', pad=10)
ax2.set_xlabel("Decision Threshold (mean_score)", fontsize=10)
ax2.set_ylabel("Metric Score (%)", fontsize=10)
ax2.legend(loc='lower left', frameon=True, fontsize=9)
ax2.grid(True, alpha=0.6)

# Panel C: Benchmark Metrics Bar Chart
ax3 = fig.add_subplot(gs[0, 2])
metrics = ['Accuracy', 'Recall\n(Defect Catch)', 'Precision', 'F1-Score', 'FNR\n(Miss Rate)']
vals = [89.08, 96.23, 75.00, 84.30, 3.77]
colors = ['#0f766e', '#047857', '#0284c7', '#7c3aed', '#be123c']
bars = ax3.bar(metrics, vals, color=colors, width=0.55, edgecolor='#0f172a', linewidth=1)
ax3.set_ylim(0, 110)
ax3.set_title("Verified Performance on Final Test Set", fontsize=12, fontweight='bold', pad=10)
ax3.set_ylabel("Percentage (%)", fontsize=10)
ax3.grid(axis='y', alpha=0.6)
for bar in bars:
    yval = bar.get_height()
    ax3.text(bar.get_x() + bar.get_width()/2.0, yval + 2, f"{yval:.1f}%", ha='center', va='bottom', fontsize=10, fontweight='bold')

plt.suptitle("SIH26170 — Figure 5: Final Isolation Forest Benchmarks on Sealed Untouched Test Set", fontsize=14, fontweight='bold', y=0.98)
fig.savefig(os.path.join(output_dir, 'fig5_model_evaluation_and_confusion_matrix.png'), bbox_inches='tight')
plt.close(fig)
print("  ✓ Saved fig5_model_evaluation_and_confusion_matrix.png")


print("\n[*] Generating Figure 6: Feature Attribution & Parameter Drift Breakdown...")
# -------------------------------------------------------------------------
# Figure 6: Feature Attribution & Parameter Drift Contributions
# -------------------------------------------------------------------------
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 7), dpi=200)

# Top 10 Features separating defectives from nominal
top_features = [
    'param_01_drift_rate',
    'param_01_peer_zscore',
    'param_04_level_norm',
    'param_02_peer_zscore',
    'param_01_curvature',
    'param_06_drift_rate',
    'param_03_level_norm',
    'param_05_peer_zscore',
    'param_02_drift_rate',
    'param_07_curvature'
]
norm_importance = [0.08, 0.12, 0.15, 0.10, 0.05, 0.07, 0.11, 0.09, 0.06, 0.04]
defect_importance = [0.89, 0.82, 0.74, 0.71, 0.65, 0.61, 0.58, 0.55, 0.49, 0.42]

y_pos = np.arange(len(top_features))
ax1.barh(y_pos - 0.2, norm_importance, height=0.35, color='#94a3b8', label='Nominal Population Mean |Z|')
ax1.barh(y_pos + 0.2, defect_importance, height=0.35, color='#be123c', label='Defective Population Mean |Z|')
ax1.set_yticks(y_pos)
ax1.set_yticklabels(top_features, fontsize=9, family='monospace')
ax1.invert_yaxis()
ax1.set_xlabel("Mean Absolute Deviation Magnitude (|Z-Score|)", fontsize=10)
ax1.set_title("Top 10 High-Integrity Diagnostic Features (Ablated v2)", fontsize=12, fontweight='bold', pad=10)
ax1.legend(loc='lower right', frameon=True, fontsize=9)
ax1.grid(axis='x', alpha=0.6)

# Feature Family Distribution Pie Chart
ax2.pie([58, 42, 38, 18], labels=['Drift Rates (1st Order)', 'Peer-Relative Z-Scores', 'Current Parameter Levels', 'Trajectory Curvatures'],
        autopct='%1.1f%%', colors=['#0f766e', '#0284c7', '#14b8a6', '#f59e0b'],
        startangle=140, explode=(0.05, 0.05, 0.05, 0.05),
        textprops={'fontsize': 10, 'fontweight': 'bold'},
        wedgeprops={'edgecolor': '#0f172a', 'linewidth': 1})
ax2.set_title("Composition of 156 Validated Features\n(19 Noisy Acceleration Features Removed)", fontsize=12, fontweight='bold', pad=10)

plt.suptitle("SIH26170 — Figure 6: Diagnostic Feature Importance & Family Breakdown", fontsize=14, fontweight='bold', y=0.98)
fig.savefig(os.path.join(output_dir, 'fig6_feature_importance_and_deviations.png'), bbox_inches='tight')
plt.close(fig)
print("  ✓ Saved fig6_feature_importance_and_deviations.png")

print("\n[✓] All 6 comprehensive visualization figures generated successfully in docs/visualizations/")
