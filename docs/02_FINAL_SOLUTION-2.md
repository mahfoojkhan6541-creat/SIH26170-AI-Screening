# SIH26170 — Final Solution
## Context-Aware AI for Burn-In Anomaly Detection & Future Drift Prediction
### Production-Oriented Engineering Baseline — Updated Final Version

**Problem Statement:** SIH26170 — AI-Driven Anomaly Detection in Component Burn-In & Screening  
**Organization:** Indian Space Research Organisation (ISRO)  
**Theme:** Smart Automation  
**Category:** Software  
**Solution role:** Decision-support layer over burn-in/screening data; the AI does not replace approved engineering authority.

---

## 0. Document Purpose and Source of Truth

This document is the Markdown transformation of the supplied **SIH26170 Final Solution Guide, Engineering Baseline v2.1**, with the project decisions and corrections discussed after that PDF incorporated into one consistent final solution definition.

### Update rules incorporated in this version

1. The core solution remains the same: **validated burn-in data → context/reference population → trajectory features → Isolation Forest + GPR → contextual evidence → explanation → QA decision → audit**.
2. The production software stack is updated to the current agreed stack: **React + Vite + Tailwind + Plotly; Python + FastAPI + Pydantic; SQLite + SQLAlchemy for the current deployment; scikit-learn; SciPy; Pandas; NumPy; Joblib; Pytest; YAML/.env; Docker**.
3. **Node.js/Express, tRPC, Drizzle ORM, MongoDB and DynamoDB are not required by the final solution.** They came from the earlier AI-generated starter repository and are not part of the final architecture.
4. **SHAP is part of the planned final explainability layer for Isolation Forest.** Current non-SHAP feature attribution can be retained during development until SHAP is verified.
5. **No synthetic data is used for model training or performance validation.** Synthetic values may be used only as clearly labelled illustrations or controlled software tests.
6. The supplied **NASA aging/degradation MAT files** are used for GPR temporal-model development after dataset profiling and mapping. An additional independent authentic temporal dataset should be used when available for stronger external generalization evidence.
7. For Module A, **D1 + D2 + SECOM** can be used as independent authentic anomaly-detection verification datasets, provided the same generalized pipeline is applied through configuration/mapping rather than dataset-specific rewrites.
8. Missing test-bench/environmental channels do **not** stop the pipeline. Available context is used; unavailable context is explicitly marked unavailable, and the system does not invent an exact physical cause.
9. **Isolation Forest anomaly thresholds, engineering specification limits, and the GPR safety-slope criterion are separate concepts.** IF does not need an engineering specification limit to learn unusual behaviour, but the overall engineering decision layer may use approved specification/safety rules when they are available.
10. The QA Q&A layer is optional future functionality. The core safety path remains deterministic and does not require an LLM.

---

# 1. Executive Summary

The problem is simple to state: a component can remain inside an absolute electrical limit while its **change over time is abnormal**. SIH26170 therefore asks for a machine-learning approach that looks at time-series behaviour rather than only a final pass/fail value.

The solution adds a context-aware AI analysis layer over the existing burn-in/screening process:

```text
Burn-in / screening measurements
            ↓
Data quality + semantic mapping
            ↓
Component / lot / test context
            ↓
Trajectory + peer/lot features
            ↓
      ┌───────────────┐
      │               │
      ▼               ▼
Isolation Forest     GPR
Abnormal now       Future trend
      │             + uncertainty
      └───────┬───────┘
              ↓
     Context / Evidence Check
              ↓
      Explanation + Rules
              ↓
 PASS / RETEST / REVIEW / REJECT
              ↓
       QA / Engineering
              ↓
          Audit trail
```

### 1.1 What is new in the final design?

The strongest system-level novelty is the **Contextual Evidence Challenge (CEC)**.

A suspicious alert is not immediately treated as a component defect. Before escalation, the system checks three views:

1. **Target trajectory** — what the component itself is doing over time.
2. **Reference population** — how the component compares with appropriate peers and its lot.
3. **Common-mode evidence** — whether a shared lot, chamber, tester, power or measurement pattern may explain the movement.

This is a proposed **system-integration and evidence workflow**, not a claim that anomaly detection or drift prediction were invented here.

### 1.2 What the system is not

- Not a replacement for approved burn-in, screening or engineering specifications.
- Not an automatic proof of physical root cause.
- Not a guarantee of future component health beyond the observed/prediction horizon.
- Not dependent on one component type, one table structure or one permanent threshold.
- Not dependent on synthetic training data.
- Not an LLM-based safety decision system.

---

# 2. Official Problem Interpretation and Requirement Traceability

| Requirement | Final solution response |
|---|---|
| **R1 — Dynamic / lot-relative anomaly detection** | Context-aware reference population + trajectory features + Isolation Forest |
| **R2 — Future drift prediction** | GPR + predictive uncertainty + configurable safety/engineering rule |
| **R3 — Sparse checkpoints** | Preserve actual event time, elapsed time and delta-time; never assume equal spacing |
| **R4 — Useful output before 168h** | Progressive inference with an explicit insufficient-evidence state |
| **R5 — Portable data schema** | Versioned semantic mapping + parameter registry + unit conversion |
| **R6 — Measurement/test confounders** | Data Quality Gate + common-mode/context evidence |
| **R7 — Different component families** | Reusable pipeline + population/profile configuration; separate model only when validation proves incompatibility |
| **R8 — Explainable output** | Feature attribution/SHAP + numerical, peer/lot, forecast and context evidence + deterministic reason engine |
| **R9 — Rare defects** | Unsupervised anomaly detection + rare-event evaluation; labels are evaluation-only where available |
| **R10 — Defensible decisions** | Versioned audit trail + human QA workflow + decision contract |

---

# 3. Research Basis, Gap and Existing Solutions

## 3.1 What research already tells us

Research and existing engineering systems already cover important pieces of the problem:

- Semiconductor manufacturing research demonstrates multivariate/time-series anomaly detection and evaluates unsupervised anomaly methods on labelled benchmark datasets.
- NASA work demonstrates time-based parameter drift screening and future-limit assessment.
- Industrial systems such as INFICON SmartFDC cover ML-based time-series/process anomaly detection.
- Commercial burn-in and test systems such as Advantest and Aehr provide automated test, burn-in and per-device monitoring infrastructure.
- Semiconductor reliability work shows that physical degradation can appear as changes in leakage, timing, resistance and related parameters before complete failure.

Therefore the solution does **not** claim that anomaly detection, drift prediction, burn-in monitoring or GPR are individually new.

## 3.2 Defensible solution gap

The proposed gap is the integration of these capabilities for the SIH26170 burn-in workflow:

> **A context-aware, explainable and traceable layer that combines sparse trajectory evidence, appropriate peer/lot comparison, current anomaly detection, future drift forecasting, predictive uncertainty, common-mode/confounder checking and conservative QA routing.**

This is a system-level integration contribution.

## 3.3 Existing solutions and what we take from them

| Existing solution / research | Useful capability | What we adopt | What remains different in our system |
|---|---|---|---|
| NASA parameter-drift work | Time-based drift + future assessment | Drift history and future-limit thinking | Add context-aware IF, GPR uncertainty, CEC, evidence and QA contract |
| ISRO/MMIC burn-in references | Burn-in process, electrical measurements, traceability | Engineering-process understanding | AI analysis is placed on top; exact internal ISRO workflow is not assumed |
| INFICON SmartFDC | ML time-series/process anomaly detection | Unsupervised monitoring principles | Target is component burn-in with component/lot context + future drift |
| Advantest 7038 STR | Automated burn-in/test infrastructure | Automation and acquisition principles | Our main contribution is analytical and decision intelligence |
| EDA MOSBTS-M / ETNA | Burn-in monitoring/history/drift | Time-history and drift analysis | Add contextual evidence and explainable QA chain |
| Aehr FOX-XP | High-throughput burn-in/test and per-DUT monitoring | Per-device traceability/monitoring concept | Focus on behaviour analysis and evidence |
| Infineon/Polimi research | Data-driven semiconductor quality prediction | Early quality-prediction direction | Add peer/lot context, confounder challenge and decision contract |

**Comparison discipline:** Do not use unverified percentage-match claims. Publicly documented capabilities must be described as documented, related/partial or not publicly verified—not as factual “No” claims when internal capability is unknown.

---

# 4. Part 1 — The Component and Its Context

## Purpose

Identify what is being tested and choose the correct comparison population.

### Case 1 — Different part types

Examples can include digital ICs, analog ICs, ASICs, processors, memory, MOSFET/IGBT power devices, regulators, sensors and mixed-signal parts.

**Solution:** Preserve **Part Type** as context. Use one reusable pipeline by default. Do not automatically create one model for every part type.

### Case 2 — Different normal ranges

A normal value for one component family can be unusual for another.

**Solution:** Use population/profile-specific reference distributions and approved engineering limits where available. Never apply one global baseline blindly.

### Case 3 — Same part number, different lots

Manufacturing variation can shift the normal centre of different lots.

**Solution:** Preserve **Lot ID** and compute:

- component vs peers in the appropriate population;
- lot vs comparable lots.

### Case 4 — Component vs lot problem

Two questions must remain separate:

1. Is this component unusual compared with its peers?
2. Is this entire lot unusual compared with comparable lots?

### Reference-population mechanism

The model does not magically know which components are comparable. The pipeline explicitly determines this through **configuration + context rules**:

```text
Target component
      ↓
Read configured context
(Part Type / Part Number / Lot / test context)
      ↓
Select compatible reference population
      ↓
Exclude target itself
      ↓
Check minimum population size
      ↓
Apply configured/as-of time rule
      ↓
Create population_id
      ↓
Generate peer/lot-relative evidence
```

Part Type is context, not an automatic instruction to create separate models.

---

# 5. Part 2 — Burn-In Test Process and Stress Context

## Purpose

Record the conditions under which each measurement was produced so environmental or test-system effects are not mistaken for component degradation.

### Relevant contexts

- Intended and actual temperature where available
- Voltage
- Current
- Frequency
- Duty cycle
- Static/dynamic operating state
- Tester/instrument identity
- Calibration state/date where available
- Fixture/contact status where available

### Seven important cases

1. **Steady temperature** — normal baseline context.
2. **Temperature wobble** — check whether the measured trend follows the environment.
3. **Temperature overshoot** — identify affected intervals and treat them carefully.
4. **Faulty sensor/calibration** — lower trust or require remeasurement.
5. **Other stress conditions** — retain as contextual variables.
6. **Bad socket/fixture/contact** — separate test-system issues from component issues.
7. **Common-mode disturbance** — if many components move together at the same time, investigate a shared effect.

### Final engineering rule

If context exists, use it. If context does not exist in a dataset, the pipeline still works using available data, but it must say that the missing context prevents that specific explanation.

The system must never fabricate a chamber temperature, calibration state or other missing test-bench information.

---

# 6. Part 3 — The Data Being Collected

## Purpose

Represent parameters, time, source and arrival correctly so the AI is portable and can operate progressively.

### Case 1 — Parameter types

Iddq, leakage current and propagation delay are examples, not a closed list.

**Solution:** Use a configurable **Parameter Registry** containing:

- parameter ID;
- external/source aliases;
- canonical internal name;
- source unit and canonical unit;
- parameter type;
- validation rules;
- model availability/requirements.

A new parameter should be added through configuration rather than rewriting the pipeline.

### Case 2 — Fixed checkpoints

The PS uses examples such as **0h, 24h, 96h and 168h**. These are sparse and unevenly spaced.

The actual intervals are:

- 0 → 24 h = 24 h
- 24 → 96 h = 72 h
- 96 → 168 h = 72 h

Therefore drift rate must use actual elapsed time.

### Case 3 — Progressive arrival

Measurements arrive over time. The system maintains state and updates its assessment when new valid data arrives.

Important distinction:

> **Not yet arrived ≠ missing ≠ zero.**

### Case 4 — Dataset mapping / portability

Different datasets may use different:

- column names;
- units;
- parameter counts;
- identifier fields;
- time representation;
- source formats.

**Solution:** Versioned semantic mapping into one canonical internal representation.

### Case 5 — Manual vs automatic entry

The source interface may be manual or equipment-generated. The pipeline therefore has a source-aware ingestion/validation boundary instead of assuming one entry method.

---

# 7. Part 4 — Data Quality Gate

## Purpose

Stop bad, ambiguous or misleading measurements before they become model evidence. Preserve raw evidence and classify quality rather than silently “repairing” it.

### Twelve data-quality cases

1. Missing reading
2. Partial missing parameter
3. Sensor/measurement error
4. Duplicate reading
5. Wrong timestamp
6. Wrong component ID
7. Wrong unit
8. Measurement saturation
9. Sensor noise/quantization
10. Communication/equipment failure
11. Out-of-order records
12. Clock mismatch

### Core flow

```text
Raw measurement
      ↓
Identity / time / unit checks
      ↓
Plausibility + integrity validation
      ↓
 ┌───────────────┐
 │               │
 ▼               ▼
VALID          INVALID/SUSPECT
 │               │
 ▼               ▼
AI-ready       Quarantine / RETEST
```

### Final rules

- Raw source data remains immutable.
- Missing future readings are never invented.
- Invalid identity/time/unit data is quarantined rather than guessed.
- Each transformed record carries quality state and provenance.
- Parameter-level quality is allowed for partial missingness.

### Quality states

`VALID`, `PARTIAL`, `MISSING`, `SUSPECT`, `INVALID`, `DUPLICATE`, `SATURATED`, `QUARANTINED`

---

# 8. Part 5 — Core Anomaly and Drift Problem

## Purpose

Detect abnormal trajectory behaviour, not only endpoint violations.

### Required behaviour patterns

| Case | What the system should do |
|---|---|
| Flat / stable | Level + low-change + reference comparison |
| Gross out-of-limit | Apply approved specification rule; AI does not replace it |
| Slow steady in-spec drift | Slope/drift + peer deviation + future forecast |
| Accelerating drift | Curvature/rate change when enough points exist + GPR |
| Late-onset step change | Step/change features + data/test checks + retest/review |
| Early jump then flatten | Full trajectory + stabilization evidence; do not automatically call it degradation |
| Non-monotonic / oscillating | Variability + amplitude + shape + peer/context comparison |
| Spike then down | Spike feature + test/context check + repeatability |
| Sudden drop | Drop feature + test/context check + retest where indicated |
| Single-parameter drift | Parameter-specific trajectory + reference comparison |
| Multi-parameter correlated drift | Joint/correlation features when supported by data |
| In-spec but peer outlier | Peer/lot deviation + trajectory + IF — core latent-defect candidate |
| Borderline/ambiguous | REVIEW rather than force PASS/REJECT |
| Too slow within 168h | State observability limitation; do not claim future health |
| Same final value, different path | Compare complete trajectories, not endpoint alone |
| Component vs own lot | Component-vs-peer evidence |
| Entire lot shifted | Lot-vs-lot/common-mode investigation |

### Hero latent-defect example

Assume a **valid approved engineering limit** of 50 µA and a target trajectory:

`10 → 25 → 40 → 45 µA`

while comparable peers remain around `10–13 µA`.

The target is still below 50 µA but is potentially anomalous relative to its appropriate reference population.

**System response:** flag evidence for QA review; do not automatically reject the part.

### Key distinction

> **“Within limit” and “normal behaviour” are different questions.**

---

# 9. Part 6 — Plausible Physical Causes of Drift

## Purpose

Connect observed electrical patterns to engineering hypotheses without pretending sparse measurements prove a root cause.

Possible mechanisms include:

1. TDDB / gate dielectric degradation
2. Electromigration
3. NBTI / HCI threshold shift
4. Weak wire bonds / package voids
5. Contamination-related leakage behaviour
6. Micro-cracks

### How these are used

```text
Observed trajectory
       ↓
Statistical evidence
       ↓
Plausible physical hypothesis
       ↓
Engineering investigation
```

A statement such as **“leakage increased and may be consistent with a degradation mechanism”** is valid evidence for investigation.

A statement such as **“the component definitely has TDDB”** is not justified from sparse anonymized measurements alone.

---

# 10. Part 7 — Confounders: Signals That Can Mislead the AI

## Purpose

Separate true component-specific evidence from manufacturing, environment, measurement and rarity effects.

### Key confounders

1. Lot-to-lot manufacturing variation
2. Chamber temperature wobble
3. Equipment/calibration drift
4. Normal early settling
5. High background variation / weak defect signal
6. Extreme rarity of confirmed defects

### Context-aware rule

An alert becomes stronger when:

- the target is unusual relative to the **correct reference population**;
- the trajectory evidence is consistent;
- common-mode evidence does **not** explain the movement;
- data quality is trustworthy.

A shared shift across a lot/chamber/tester should instead trigger **systemic investigation evidence**.

### Important data-availability rule

The solution is designed to work with whatever context is supplied.

For example:

- Temperature available → temperature-aware context analysis.
- Tester ID available → tester-wide common-mode analysis.
- Lot ID available → lot-relative evidence.
- None available → analyse available measurements, report the missing context, and avoid claiming an exact physical cause.

---

# 11. Part 8 — Modeling and Decision Design

## Purpose

Keep the current anomaly question and future prediction question separate until evidence fusion.

### Module A — Isolation Forest

**Question:**

> “Is this behaviour unusual right now, relative to its appropriate reference population?”

Inputs include validated behaviour/context features. Labels are **not** supplied to the Isolation Forest model as target features.

### Module B — Gaussian Process Regression

**Question:**

> “Given the available history, where is the parameter heading?”

GPR returns:

- predicted future value;
- predictive uncertainty;
- trajectory/forecast evidence.

The model is only used when the available history satisfies the validated minimum-evidence policy.

### Progressive forecasting

```text
0h data
  ↓
Initial state
  ↓
New checkpoint
  ↓
Update trajectory
  ↓
Update GPR forecast + uncertainty
  ↓
Update evidence/decision
```

No future value is invented when a checkpoint has not arrived.

### Uncertainty

The GPR implementation reports predictive uncertainty; the dashboard may show an uncertainty band such as **mean ± 2σ** when the configuration calls for it.

### Threshold / contamination

Isolation Forest still needs a decision cutoff. That cutoff is an operational/configuration choice and must be selected from training/validation evidence and engineering objectives.

**Do not confuse:**

- IF anomaly threshold;
- engineering specification limit;
- GPR safety-slope criterion.

They serve different purposes.

### IF training/evaluation rule

```text
TRAIN
labels excluded from model fitting
        ↓
Isolation Forest learns structure of reference data
        ↓
VALIDATION
labels may be used only to evaluate/calibrate threshold
        ↓
FREEZE
        ↓
FINAL TEST
labels are used only after prediction to calculate metrics
```

### Metrics

For labelled benchmark datasets:

- Recall / sensitivity
- False-negative rate
- Precision
- False-positive rate
- F1
- Confusion matrix
- Precision-recall behaviour

For GPR:

- MAE
- RMSE where useful
- prediction-interval coverage/calibration when uncertainty is reported
- error by forecast horizon

---

# 12. Part 9 — What Correct Looks Like

## Four operational states

| State | Meaning |
|---|---|
| **PASS** | Evidence acceptable under approved rules and current tested context |
| **RETEST** | Measurement/data trust is insufficient; repeat or repair the measurement path |
| **REVIEW** | Evidence is valid but uncertain or ambiguous; human engineering/QA review required |
| **REJECT** | High-risk/rejection recommendation under validated rules; final authority remains with approved engineering procedure |

### Why this matters

A binary PASS/FAIL result cannot distinguish:

- bad measurement;
- uncertain evidence;
- strong abnormal evidence.

### Evaluation focus

Because the PS treats a false negative as catastrophic, the system must prominently evaluate and monitor **recall/sensitivity and false-negative rate**, not accuracy alone.

### Engineering rule

A model result is a **recommendation with evidence**, not automatic mission acceptance authority.

---

# 13. Part 10 — Real-World Deployment Constraints

## Purpose

Make the system portable, checkpoint-aware, configurable, human-supervised and auditable.

### Case 1 — Real-time / streaming

`ingest → validate → append → update anomaly → update forecast → update decision → log`

The system can produce useful intermediate information when sufficient evidence exists and otherwise returns an explicit insufficient-evidence/monitor state.

### Case 2 — Dataset mapping / portability

A new dataset should be connected using configuration and semantic mapping rather than source-specific rewrites.

### Case 3 — Threshold recalibration

Proxy thresholds are provisional. When representative target data becomes available:

`collect → validate → calibrate → approve → version → deploy`

### Case 4 — Generalization across part types

Use population-aware configuration and registered profiles. One global model/threshold is not assumed to fit every family.

### Case 5 — Human-in-the-loop

RETEST/REVIEW/high-risk cases go to the responsible QA/engineering workflow.

### Case 6 — Traceability / auditability

Store enough information to reconstruct the decision later.

---

# 14. Unified End-to-End Production Architecture

## Data Trust → Intelligence → Evidence → QA

```text
┌──────────────────────── DATA + TRUST ────────────────────────┐
│ Burn-in measurements                                          │
│ 0h / 24h / 96h / 168h or available checkpoints               │
│                                                              │
│ Component / Part / Lot / Test context                        │
│                                                              │
│ Ingestion + semantic mapping + unit conversion                │
│                                                              │
│ Data Quality Gate + provenance                                │
└────────────────────────────┬─────────────────────────────────┘
                             ↓
┌──────────────────────── AI + CONTEXT ────────────────────────┐
│ Reference population selection                                │
│                                                              │
│ Feature / behaviour engine                                   │
│ level · delta · slope · curvature · variability               │
│ peer/lot deviation · cross-parameter relations               │
│                                                              │
│ Isolation Forest                GPR                           │
│ abnormal now                    future trend + uncertainty     │
│                                                              │
│ Contextual Evidence Challenge                                 │
│ own trajectory + peer/lot + common-mode evidence             │
└────────────────────────────┬─────────────────────────────────┘
                             ↓
┌──────────────────── DECISION + QA ───────────────────────────┐
│ Evidence Engine                                               │
│ model evidence + quality + context + approved rules           │
│                                                              │
│ Explainability                                                │
│ SHAP/feature contribution + numerical + graph evidence       │
│                                                              │
│ Decision contract                                             │
│ PASS / RETEST / REVIEW / REJECT                               │
│                                                              │
│ Human QA / Engineering final disposition                     │
│                                                              │
│ Audit + monitoring + controlled recalibration                 │
└───────────────────────────────────────────────────────────────┘
```

### Architecture principle

Each logical layer has one responsibility:

`data → validated context → behaviour → models → evidence → decision → QA → audit`

---

# 15. Data Contract and Feature Definitions

## 15.1 Canonical record

| Field | Status | Meaning |
|---|---|---|
| `component_id` | Required | Unique component identity |
| `part_type` | Context | Component family/type |
| `part_number` | Context | Exact part identity where available |
| `lot_id` | Context | Manufacturing/test grouping |
| `test_run_id` | Context | Screening/burn-in run |
| `parameter_id` | Required | Canonical measurement concept |
| `value` | Required | Source measurement |
| `original_unit` | Required when present | Unit as received |
| `canonical_value` | Derived | Converted/validated value |
| `canonical_unit` | Derived | Common model unit |
| `checkpoint` | Required when available | Burn-in stage/checkpoint |
| `event_time` / `elapsed_time` | Required when available | Actual measurement time |
| `stress_context` | Recommended | Temperature, voltage, current, frequency, duty cycle, operating state |
| `equipment/source_id` | Recommended | Measurement provenance |
| `quality_state` | Required | VALID/PARTIAL/MISSING/etc. |
| `provenance` | Required | Source + mapping + transformation history |

## 15.2 Time-aware mathematics

For measurement `y_i` at elapsed time `t_i`:

```text
Δy_i = y_i − y_(i−1)

s_i = Δy_i / (t_i − t_(i−1))
```

The actual elapsed interval is always used.

For a conceptual peer-relative standardized feature:

```text
z_peer = (y − m_peer) / s_peer
```

where the peer statistics come from a valid, comparable reference population.

The exact robust estimator is a deployment calibration choice, not a universal fixed formula.

## 15.3 Feature families

- Level/current value
- Delta/change
- Drift/slope
- Acceleration/curvature when enough points exist
- Variability/oscillation
- Spike/drop magnitude
- Stabilization/plateau
- Trajectory shape
- Peer deviation
- Lot deviation
- Cross-parameter relationships when supported by data
- Context/confounder evidence

---

# 16. Model Training, Validation and Dataset Strategy

## 16.1 Module A — Isolation Forest datasets

Current anomaly-detection validation strategy:

- **D1** — authentic semiconductor manufacturing dataset for anomaly-method development.
- **D2** — authentic semiconductor manufacturing dataset for anomaly-method development and held-out evaluation.
- **SECOM** — independent authentic semiconductor manufacturing dataset for additional Module A verification.

These datasets are not treated as ISRO production data. Their role is to test the generalized anomaly-detection methodology across different authentic data structures.

### Rule

Do not merge structurally different datasets blindly. Each dataset enters through the same configuration-driven pipeline with its own mapping/profile.

## 16.2 Module B — GPR dataset strategy

The supplied **seven NASA aging/degradation MAT files** are used as the temporal/degradation dataset family for GPR development.

Before training:

1. inspect every MAT file;
2. identify component/cell/device identity;
3. identify time/cycle information;
4. identify repeated measurements;
5. identify usable degradation parameters;
6. inspect units and missingness;
7. define the forecast target;
8. construct history → future samples;
9. split by component/device where appropriate to prevent trajectory leakage;
10. train and validate GPR;
11. evaluate held-out forecasts using MAE;
12. record uncertainty behaviour.

### Additional GPR generalization evidence

A second independent authentic temporal degradation/aging dataset should be used for stronger cross-dataset validation when available. A dataset qualifies only if it contains enough repeated temporal measurements to support meaningful forecasting.

## 16.3 No synthetic model training

Synthetic numerical examples are allowed only for:

- illustrations;
- unit tests;
- edge-case testing;
- UI demonstrations clearly labelled as synthetic.

Synthetic data must never be presented as evidence of model performance.

## 16.4 Training protocol

```text
TRAIN
  ↓
Fit preprocessing
  ↓
Train model
  ↓
VALIDATION
  ↓
Tune/calibrate configuration
  ↓
FREEZE
  ↓
FINAL TEST
```

Preprocessing is fitted only on training data. Final-test labels never select the threshold or contamination.

## 16.5 Cross-dataset generalization claim

The defensible claim is:

> **The same configuration-driven pipeline and modelling methodology are evaluated on multiple independent authentic datasets, with dataset-specific mapping rather than dataset-specific rewrites.**

This is stronger and more scientifically appropriate than claiming that a model “works for every component type.”

---

# 17. Explainability, CEC and Decision Contract

## 17.1 Explainability architecture

```text
Isolation Forest
      ↓
SHAP / feature contribution
      +
Peer/lot deviation
      +
Trajectory evidence
      +
GPR forecast + uncertainty
      +
Context/common-mode evidence
      ↓
Evidence Engine
      ↓
Plain-English reason
      ↓
QA view
```

### SHAP

SHAP is the planned exact feature-attribution mechanism for the Isolation Forest branch.

It answers:

> **Which features contributed to this model output, and in which direction?**

Until SHAP is verified in the running model, existing peer-relative attribution may be retained as an interim explanation—but the final target includes SHAP.

### GPR explanation

GPR does not need SHAP. Its explanation is based on:

- observed trajectory;
- forecasted value;
- predictive uncertainty;
- drift/slope evidence;
- forecast horizon;
- engineering/safety criterion where available.

### Deterministic Evidence Engine

A language model is not required for the core safety path.

The evidence engine converts machine evidence into simple statements such as:

> “The component shows a persistent upward drift and is substantially above comparable peers.”

or:

> “The forecast remains uncertain because only limited history is available.”

---

# 18. Decision and QA Workflow

```text
Validated evidence
        ↓
Quality + context check
        ↓
IF anomaly evidence + GPR forecast evidence
        ↓
Engineering rules / safety criteria
        ↓
┌─────────┬─────────┬─────────┬─────────────┐
│ PASS    │ RETEST  │ REVIEW  │ REJECT REC. │
└─────────┴─────────┴─────────┴─────────────┘
        ↓
Human QA / Engineering
        ↓
Final disposition
        ↓
Audit record
```

### Decision semantics

**PASS** — evidence acceptable under configured/approved rules.

**RETEST** — data or measurement path is not trustworthy enough for a safe decision.

**REVIEW** — evidence is valid but uncertain/ambiguous or context requires human judgment.

**REJECT recommendation** — validated high-risk criteria are satisfied. Final authority remains with the approved engineering procedure.

### Required review evidence

For a REVIEW or high-risk case, the system should show:

- component identity/context;
- current measurement;
- trajectory;
- anomaly score;
- peer/lot comparison;
- SHAP/feature contribution;
- GPR forecast;
- predictive uncertainty;
- relevant confounder/common-mode evidence;
- data-quality state;
- configured rule/limit when available;
- reason code;
- timestamp and model/config versions.

---

# 19. Final Technology Stack

## Current development / working-model stack

| Layer | Final technology |
|---|---|
| Frontend | **React + Vite** |
| UI styling | **Tailwind CSS** |
| Charts | **Plotly** |
| Backend API | **Python + FastAPI** |
| API validation | **Pydantic** |
| ML language | **Python** |
| Anomaly detection | **scikit-learn — Isolation Forest** |
| Drift prediction | **scikit-learn — GaussianProcessRegressor** |
| Data processing | **Pandas + NumPy** |
| MAT dataset handling | **SciPy `loadmat`** |
| Model persistence | **Joblib** |
| Current database | **SQLite + SQLAlchemy** |
| Configuration | **YAML + `.env`** |
| Testing | **Pytest** |
| Deployment | **Docker** |
| Explainability | **SHAP + deterministic evidence engine** |

### Production-cloud note

Development should remain free/local using open-source components.

For actual organizational deployment, enterprise database/object-storage/cloud infrastructure can be introduced later according to approved ISRO infrastructure and security requirements. Do not treat AWS RDS/S3 as currently deployed unless they are actually deployed.

### Not part of final architecture

The following are **not required** by SIH26170 and should not be retained merely because the first AI-generated starter repository used them:

- Node.js/Express
- tRPC
- Drizzle ORM
- MongoDB
- DynamoDB
- Next.js

The final system uses React/Vite + FastAPI/Pydantic + SQLite/SQLAlchemy for the current working baseline.

---

# 20. Deployment and Failure Isolation

## Current logical service boundaries

```text
React / Vite
     ↓
FastAPI / Pydantic
     ↓
Core processing + model services
     ↓
SQLite audit / traceability
```

### Failure rule

If the ML service fails:

- preserve the input record;
- log the failure;
- return a safe error/hold state;
- never manufacture a PASS result.

### Production evolution

The same logical boundaries can later be deployed as separate processes/containers if the target environment requires scale, isolation or organizational integration.

Service isolation is an **architectural property**, not something guaranteed by Next.js versus Vite.

---

# 21. API and Database Contract

## 21.1 Logical APIs

| Endpoint | Purpose | Expected output |
|---|---|---|
| `POST /ingest` | Receive checkpoint/batch | Source reference + quality result + canonical ID |
| `POST /validate` | Run data-quality checks | Errors + quarantine information + provenance |
| `POST /screen` | Run current screening | IF evidence + GPR forecast/uncertainty + decision + explanation |
| `POST /train` | Train configured profile | Model artifact + validation metrics |
| `POST /evaluate` | Evaluate frozen model | Metrics + calibration summary |
| `GET /components/{id}` | Read component history | Trajectory + peer/lot context + decisions |
| `GET /audits/{id}` | Reconstruct decision | Versions + evidence + QA history |

## 21.2 Logical database entities

- `components`
- `part_profiles`
- `lots`
- `test_runs`
- `measurements`
- `quality_events`
- `mappings`
- `model_registry`
- `model_runs`
- `screening_decisions`
- `audit_events`
- `qa_actions`

---

# 22. Validation and Test Plan

## 22.1 Data quality

Test all 12 data-quality cases, including:

- identity corruption;
- wrong time;
- unit mismatch;
- saturation;
- duplicates;
- missingness;
- clock mismatch;
- invalid measurements.

Confirm that raw data remains unchanged and transformed records carry provenance.

## 22.2 Model tests

### Isolation Forest

- label leakage test;
- grouped component split test;
- threshold-selection test;
- reference-population test;
- population-size/fallback test;
- multi-dataset configuration test;
- explanation reproducibility test.

### GPR

- no future-target leakage;
- component/device-level temporal split;
- sufficient-history test;
- progressive checkpoint test;
- prediction + uncertainty test;
- MAE test;
- forecast-horizon test.

### End-to-end

- ingest → validation → mapping → models → evidence → decision;
- audit replay;
- API integration;
- frontend result rendering;
- failure/hold behaviour.

## 22.3 Metrics

### Module A

Recall, FNR, precision, FPR, F1, confusion matrix, PR behaviour, class prevalence.

### Module B

MAE, RMSE where useful, interval coverage/calibration where uncertainty is claimed.

### Operational

PASS/RETEST/REVIEW/REJECT rates, review workload, reproducibility and latency.

---

# 23. Risk Register — Core Risks and Controls

| Risk | Impact | Primary control |
|---|---|---|
| False negative | Defect may escape | Trajectory + peer evidence + forecast + conservative validation; target-data validation |
| False positive | Good component receives unnecessary attention | Context + confounder checks + validated threshold + REVIEW/RETEST |
| Dataset shift | Model behaves differently on target data | Target-data calibration/revalidation + population profiles |
| Poor measurement quality | AI learns tester/environment artefacts | Data Quality Gate + measurement/context evidence |
| Forecast overconfidence | Future risk overstated | GPR uncertainty + minimum-evidence policy |
| Wrong identity/time | Trajectory silently corrupted | Identity/time integrity + provenance |
| Threshold misuse | Unsafe operation | Versioned configuration + validation + approval |
| Model drift | Production behaviour changes | Monitoring + controlled recalibration |
| AI over-authority | Recommendation treated as final acceptance | Human QA authority + decision contract |
| Missing context | Exact cause cannot be established | Explicit context availability state; no invented cause |
| Explanation mismatch | Engineer distrusts model | Deterministic evidence + versioned replay + SHAP where enabled |

---

# 24. Next-Round PPT, Video and Working Model

## 24.1 PPT content

The presentation should be built for fast judging, not as a condensed implementation guide.

Recommended story:

1. **Problem** — hidden abnormal trajectory can remain inside an absolute limit.
2. **Solution** — Module A: Isolation Forest; Module B: GPR; context/evidence; QA.
3. **Technical approach** — one clean process flow + technology logos.
4. **Proof** — real implementation, real validation metrics and genuine screenshots.
5. **Impact/feasibility/future** — practical value, target-data calibration and deployment path.

### Hero PPT idea

Show one **below-limit but abnormal** component:

```text
Absolute limit
────────────────────────
Target:   10 → 25 → 40 → 45
Peers:     10 → 11 → 12 → 13

IF:     unusual relative to peers
GPR:    future trajectory + uncertainty
CEC:    common-mode explanation checked
QA:     REVIEW recommendation
```

The numerical example must be clearly labelled **illustrative** unless generated from an actual dataset and approved engineering limit.

## 24.2 Video storyline

Show the real system working:

`ingest → validation → context → trajectory → current anomaly → future forecast → CEC/context evidence → explanation → QA recommendation → audit replay`

The video should demonstrate the product, not just read the PPT.

## 24.3 Working-model status

The working model should be reported using a truthful current status. Distinguish:

- implemented and verified;
- implemented but awaiting integration;
- planned enhancement;
- target-data validation required.

Do not use a completion percentage as a performance metric.

---

# 25. GitHub and Documentation Structure

```text
sih26170/
│
├── frontend/
├── backend/
├── ml/
│   ├── anomaly/
│   ├── forecast/
│   ├── features/
│   └── validation/
│
├── data/
│   ├── raw/
│   │   ├── D1/
│   │   ├── D2/
│   │   ├── SECOM/
│   │   └── NASA_GPR/
│   ├── processed/
│   ├── schemas/
│   └── sample/
│
├── models/
├── configs/
│   ├── mappings/
│   ├── thresholds/
│   ├── populations/
│   ├── profiles/
│   └── model_registry.json
│
├── tests/
├── scripts/
├── docker/
├── docs/
│   ├── 01_OFFICIAL_PS.md
│   ├── 02_FINAL_SOLUTION.md
│   ├── 03_DATA_PIPELINE_IMPLEMENTATION_GUIDE.md
│   ├── SRS.md
│   ├── ARCHITECTURE.md
│   ├── API.yaml
│   ├── DATABASE.md
│   ├── MODEL_CARD.md
│   ├── DATA_CARD.md
│   ├── TEST_PLAN.md
│   ├── DEPLOYMENT.md
│   ├── RUNBOOK.md
│   └── CHANGELOG.md
│
├── risk/
│   └── RISK_REGISTER.xlsx
│
├── results/
├── README.md
├── docker-compose.yml
├── .env.example
└── .gitignore
```

### Documentation roles

`README.md` — quick setup and project overview.

`SRS.md` — functional/non-functional requirements and acceptance criteria.

`ARCHITECTURE.md` — services, data flow, boundaries and failure isolation.

`API.yaml` — versioned API contract and field semantics.

`DATABASE.md` — entities, keys, indexes, quality states and audit relations.

`MODEL_CARD.md` — IF/GPR purpose, training data, metrics, limitations and approved use.

`DATA_CARD.md` — D1/D2/SECOM/NASA provenance, structure, mapping and limitations.

`RISK_REGISTER.xlsx` — AI/system risks, impact, controls, owners and status.

`TEST_PLAN.md` — data, model, API, integration and deployment tests.

`DEPLOYMENT.md` — container, configuration, release and rollback procedures.

`RUNBOOK.md` — operational failure handling and incident response.

`CHANGELOG.md` — versioned changes with model/config/schema impact.

---

# 26. Definition of Done

The final solution is complete when:

1. All ten solution Parts and their cases are addressed by an implementation, test, dependency control or explicit open question.
2. The Data Quality Gate protects the model from identity/time/unit and other data-quality failures.
3. Reference-population selection is explicit, configurable and auditable.
4. Isolation Forest is independently benchmarked using leakage-safe grouped validation.
5. GPR is independently evaluated on an authentic temporal dataset with valid forecast targets.
6. IF and GPR are evaluated separately before evidence fusion.
7. Progressive sparse-checkpoint inference does not fabricate future readings.
8. CEC/context checks are implemented for available context and degrade gracefully when context is absent.
9. SHAP explainability is integrated and verified for the IF branch before being claimed as operational.
10. Thresholds and configurations are versioned and calibrated using validation evidence.
11. PASS/RETEST/REVIEW/REJECT recommendation semantics are implemented.
12. Human QA authority is preserved.
13. The audit record can reconstruct how a result was produced.
14. API and frontend integration work end-to-end.
15. Monitoring and controlled recalibration are defined.
16. Real target-domain data is used for final calibration and revalidation before controlled production use.

---

# 27. Open Programme Questions — Never Guess

The following remain configurable until the actual programme provides verified information:

- exact ISRO data interface;
- actual column names and units;
- exact parameter set;
- component/lot/test identifiers;
- exact production part families;
- actual burn-in recipe and test conditions;
- approved engineering specification limits;
- approved GPR safety-slope definition;
- actual defect prevalence;
- acceptable false-positive/false-negative trade-off;
- QA authority and RETEST/REVIEW procedure;
- security/network constraints;
- audit retention/access rules.

The solution must not invent these values.

---

# 28. Final Engineering Position

```text
Existing burn-in / screening
            ↓
Validated data + context
            ↓
Reference population + trajectory
            ↓
     ┌──────┴──────┐
     ↓             ↓
    IF            GPR
 abnormal now   future trend
     ↓             ↓
     └──────┬──────┘
            ↓
Contextual Evidence Challenge
            ↓
Explainable Evidence
            ↓
PASS / RETEST / REVIEW / REJECT
            ↓
QA / Engineering
            ↓
Audit + Monitoring
```

### Final one-line solution definition

> **A context-aware, checkpoint-aware burn-in intelligence layer that validates measurements, compares each component with an appropriate reference population, detects unusual behaviour with Isolation Forest, forecasts future drift with GPR and predictive uncertainty, checks common-mode/context evidence, explains the result with SHAP and deterministic evidence, and routes a traceable recommendation to QA without replacing approved engineering authority.**

---

# References

1. Smart India Hackathon 2026 — SIH26170 public problem record / official programme material.
2. SIH26170 Research-to-Prototype Guide (project source).
3. Furnari et al., *An Ensembled Anomaly Detector for Wafer Fault Detection*, Sensors 21 (2021), 5465. DOI: https://doi.org/10.3390/s21165465
4. STMicroelectronics / Furnari D1/D2 dataset repository: https://github.com/STMicroelectronics/ST-AWFD
5. NASA parameter drift screening document: https://ntrs.nasa.gov/citations/19730015127
6. INFICON SmartFDC: https://www.inficon.com/en/products/intelligent-manufacturing-systems/smartfdc
7. Advantest 7038 STR: https://www.advantest.com/en/products/component-test-system/system-level-test-system/7038-str/
8. EDA Industries ETNA MOSBTS-M180: https://www.eda-industries.net/en/products-and-technologies/etna-mosbts-m180/
9. Aehr Test Systems burn-in/test solutions: https://www.aehr.com/solutions/die-level-test-and-burn-in-solutions/
10. Infineon / Politecnico di Milano, *A data-driven modelling framework for predicting the quality of semiconductor devices to support burn-in decisions*, Computers & Industrial Engineering 204 (2025), 111115. DOI: https://doi.org/10.1016/j.cie.2025.111115
11. Rasmussen, C. E. and Williams, C. K. I., *Gaussian Processes for Machine Learning*, MIT Press, 2006: https://gaussianprocess.org/gpml/
12. Lundberg, S. M. and Lee, S.-I., *A Unified Approach to Interpreting Model Predictions*, NeurIPS (2017): https://proceedings.neurips.cc/paper/2017/hash/8a20a8621978632d76c43dfd28b67767-Abstract.html
13. Liu, F. T., Ting, K. M. and Zhou, Z.-H., *Isolation Forest*, IEEE ICDM (2008).
14. NASA PCoE electronics datasets: https://www.nasa.gov/intelligent-systems-division/discovery-and-systems-health/pcoe/pcoe-data-set-repository/
15. NASA EEE-Parts assurance standard: https://standards.nasa.gov/standard/NE/NASA-STD-873910
16. Existing Solution References sheet (project source), with the qualification that internal capabilities not publicly verified should not be stated as factual negatives.

---

## Final consistency rule

When implementing or presenting this solution, always preserve the distinction between:

**Source fact** — directly supported by the official PS, dataset documentation, research paper, or verified implementation evidence.

**Engineering design choice** — a proposed mechanism selected for this solution.

**Illustrative example** — a synthetic/example scenario used only to explain the idea.

**Open question** — information not yet supplied by the target programme.

This distinction prevents the system, documentation and PPT from making claims stronger than the available evidence.
