# PS 26170 — Master Problem Breakdown
## Parts + Complete Case List (Final, Updated Version)

This is the final, corrected version of the problem breakdown. It includes everything discussed so far, including the two confusions that were just cleared up (scope = burn-in only, and the real-time/dataset-mapping issue). Use this as the master reference — every teammate's understanding work should map back to one of these parts.

---

## The Problem Statement, restated in simple words

Space parts are baked at a high temperature for many hours (burn-in) to force out weak parts before they go to space. While this baking happens, some numbers are measured at fixed points in time — for example at 0 hours, 24 hours, 96 hours, and 168 hours. The old method just checks: "is each number inside the allowed range?" If yes, the part passes. The problem: some bad parts stay inside the allowed range at every single check, but the way their numbers change over time is not normal. These parts pass the old test and can fail later, in space, where nobody can fix them. Our job: build an AI that looks at the pattern of change over time, not just the final number, to catch these hidden bad parts.

**Scope note (confirmed):** The PS mentions ESS (environmental stress screening) as the general category, and burn-in as one type inside it. Other ESS types exist (thermal cycling, vibration/mechanical shock), but the actual data and task described in the PS (readings at 0h/24h/96h/168h, steady elevated temperature) is specifically about **burn-in only**. This project is scoped to burn-in. Other ESS types can be mentioned as future extension, not built now.

---

## PART 1 — The Component (what is being tested)

**All cases:**
1. Different part types are possible: digital ICs, analog ICs, ASICs, processors, memory chips, power devices (like MOSFETs, IGBTs), voltage regulators, sensors, mixed-signal parts.
2. Each part type has a different "normal" range — you cannot use the same limits for a power device and a digital chip.
3. Same part number, but made in different manufacturing batches/lots — normal batch differences must not be confused with a real defect.
4. A problem can exist at the level of ONE component, or at the level of an ENTIRE LOT/BATCH — these are two different questions:
   - "Is this one part abnormal compared to its own lot?"
   - "Is this whole lot abnormal compared to other lots?"

**Diagram to make later:** a simple picture showing one component sitting inside a lot, sitting inside a batch — like nested boxes.

---

## PART 2 — The Burn-In Test Process (the stress applied)

**All cases:**
1. Ideal case — temperature held perfectly steady (e.g. 125°C) for the whole test.
2. Real case — temperature wobbles slightly up and down during the test (this is normal chamber behaviour).
3. Overshoot case — chamber temperature goes higher than planned for a while.
4. Faulty sensor/calibration case — the chamber says 125°C, but the real temperature is different; this can wrongly blame the component for something the equipment caused.
5. Other stress types besides temperature: voltage, current, frequency of operation, duty cycle, whether the part is actively switched on and working ("dynamic" burn-in) or just sitting under bias with no activity ("static" burn-in). Each type can expose different kinds of hidden defects.
6. Bad socket/fixture/contact case — the part itself is fine, but the test connection is loose or dirty, causing jumpy or missing readings (a test-system problem, not a component problem).
7. Common-mode disturbance case — if MANY components show the same unusual reading at the exact same time, it likely means the chamber or power supply had a problem, not that all those parts failed at once.

**Diagram to make later:** temperature-vs-time graph with 3 versions side by side — ideal flat line, realistic wobbly line, and one with an overshoot spike.

---

## PART 3 — The Data Being Collected (what we measure, and how it actually arrives)

**All cases:**
1. Parameter types: standby current (Iddq), leakage current, propagation delay. The PS says "e.g." meaning other parameters (like threshold voltage shift, output drive strength, gain) also count — the system should not be hardcoded to only these three.
2. Fixed checkpoints: 0h, 24h, 96h, 168h — note the spacing is uneven (not every 24 hours equally), and this is a very short, sparse time series (only 4 points), not thousands of continuous sensor readings.
3. **Real-time arrival case (important, newly clarified):** In a real setting like ISRO, the data does NOT exist all at once as a finished table. The 0h reading happens first, then 24 hours pass before the next reading exists, and so on. The system needs to be able to make a prediction using whatever readings exist so far — it cannot wait for all 4 points to be available before saying anything useful.
4. **Dataset structure/mapping case (important, newly clarified):** The dataset your team trains on (public/proxy data) will very likely have different column names, units, and even a different number of parameters than ISRO's real data. Your team does not currently know ISRO's actual column structure. This means the system's design should not hardcode exact column names — it needs a way to "map" a new dataset's fields to the system's internal concepts (component ID, timestamp/interval, parameter values) so it can be reused on a differently-structured dataset without a full rebuild.
5. Manual vs automatic data entry case — it is not yet known whether real screening data is entered manually by a person or logged automatically by test equipment. This affects how strict our data validation step needs to be, and is currently an open question to research, not something to assume.

**Diagram to make later:** a timeline picture showing data "arriving" at 0h, then 24h, then 96h, then 168h — with a note at each point saying "system must be able to give an answer using only what exists so far."

---

## PART 4 — Data Quality Problems (all the ways the numbers can be wrong before AI even sees them)

**All cases:**
1. Missing reading (e.g. 96h value never recorded).
2. Partial missing (one parameter missing, others fine).
3. Sensor/measurement error (a reading that is physically impossible).
4. Duplicate reading (same value recorded twice).
5. Wrong timestamp (96h data accidentally labeled as 24h).
6. Wrong component ID (data from one part attached to a different part's record) — the most dangerous case, since it can silently corrupt everything even if the model is otherwise correct.
7. Wrong unit (µA mixed with mA, ns mixed with µs).
8. Measurement saturation (instrument reaches its maximum/minimum and cannot read any higher/lower).
9. Sensor noise/quantization (small random jitter in every reading).
10. Communication/equipment failure (corrupted or incomplete data block).
11. Out-of-order records (96h data arrives before 24h data in the file).
12. Clock mismatch between different test instruments.

**Diagram to make later:** a flowchart — "Raw Reading" → box showing all 12 possible failure points → "What Actually Reaches the Model."

---

## PART 5 — The Core Anomaly/Drift Problem (the actual heart of the PS)

**The main distinction:** old method checks if a NUMBER crosses a LINE. The real, hard problem is whether the SHAPE of change over time is normal — even when no line is ever crossed.

**All trajectory patterns (cases) that must be told apart:**
1. Flat/stable — barely changes. Healthy.
2. Gross out-of-limit — crosses the spec line directly. Old method already catches this; not the interesting case.
3. Slow steady drift, staying inside the allowed range the whole time.
4. Accelerating drift — slow change at first, then speeding up.
5. Late-onset step change — flat for a long time, then jumps only at the last checkpoint (168h).
6. Early jump, then flattens out/recovers.
7. Non-monotonic/oscillating — goes up, down, up, down.
8. Sudden spike that comes back down.
9. Sudden drop.
10. Single-parameter drift — only ONE measured value (say Iddq) moves, others stay flat.
11. Multi-parameter correlated drift — two or more parameters (say Iddq and delay) drift together.
12. **In-spec but stands out compared to other similar parts — this is the literal definition of "latent defect" from the PS title. The single most important case in the whole project.**
13. Borderline/ambiguous case — right near the decision cutoff line, not clearly normal or abnormal.
14. Defect too slow to fully show up by 168h — a real and honest limitation of any model built on this data, not a bug to hide.
15. Same final value at 168h, but a very different path in between two different parts.
16. One part compared against its own lot/batch peers.
17. An entire lot/batch shifted compared to other lots.

**Example to build later:** worked numeric examples (made-up but realistic numbers) for cases 3, 4, 5, and 12 especially — these four best explain why this project needs to exist.

**Diagram to make later:** one big grid of small line-graphs, one tiny graph per case above (a 4x5 grid), each clearly labeled. This should become your most important single slide.

---

## PART 6 — Real Physical Causes of Drift (why this actually happens)

**All cases:**
1. Gate oxide slowly wearing out (TDDB — Time-Dependent Dielectric Breakdown) → rising leakage/Iddq.
2. Metal wiring inside the chip thinning over time (electromigration) → rising delay, eventually a broken connection.
3. Threshold voltage shifting (NBTI / Hot Carrier Injection) → delay and leakage drifting together.
4. Weak wire bonds or voids inside the package → intermittent, jumpy readings.
5. Contamination (stray particles/ions) inside the package → slow leakage drift, worse with heat.
6. Micro-cracks caused during manufacturing/cutting → can show up as a sudden step-change pattern.

**Table to make later:** two columns — "Physical Cause" and "Which trajectory pattern (from Part 5) it usually produces."

---

## PART 7 — Confounders (things that LOOK like a defect but are NOT, and the reverse)

**All cases:**
1. Normal batch-to-batch manufacturing variation, mistaken for a defect.
2. Chamber temperature not being perfectly steady, causing a fake-looking drift.
3. Test equipment calibration drifting slightly over the days between the first and last reading.
4. A normal "settling in" effect in the first 24 hours, mistaken for a defect.
5. Background/intrinsic leakage on modern parts being so high that a real defect's extra leakage gets buried in noise and becomes invisible (the defect is real but the signal is too weak to see).
6. Extreme rarity of real confirmed defects (parts-per-million level) — a fact about the real world, not a modeling choice, and it affects everything about how the AI must be built.

---

## PART 8 — The Modeling/Decision-Design Problem (choices the team must make on purpose)

**All cases:**
1. Detection question — "is this trajectory abnormal right now, given the points collected so far?"
2. Forecasting question — "based on the trend so far, where is this heading, and will it cross a danger line later?" These are two different questions, not one.
3. Supervised learning — needs many labeled bad examples; NOT realistic here because real defects are extremely rare.
4. Unsupervised/anomaly-detection learning — learns what "normal" looks like and flags anything unusual; realistic choice given how rare real defects are.
5. **The threshold/contamination decision case (newly clarified):** any anomaly-detection method needs a cutoff — a number saying "what fraction of parts do we expect to be abnormal?" (in Isolation Forest, this is called "contamination"). This number is NOT learned from truth by the algorithm — it is an engineering judgment call, based on known/expected defect rates, sensitivity testing (trying a few different values and seeing what changes), and how much risk the team is willing to accept. This must be clearly explained and justified in the report, not hidden as if the model "figured it out" on its own.
6. Single-parameter vs multi-parameter modeling — checking each measured value separately (simpler, easier to explain) vs checking them together as one combined pattern (catches correlated drift, case 11 in Part 5).
7. Explainability requirement — a plain "abnormal" flag is not enough for an engineer deciding whether to scrap an expensive space part; the system should be able to show WHY a part was flagged (which parameter, how much it contributed).

---

## PART 9 — What "Correct" Looks Like (requirements the final output must satisfy)

**All cases:**
1. A plain pass/fail is not enough. Needed instead: PASS, RETEST (data was untrustworthy, redo the measurement), REVIEW (genuinely uncertain, send to a human), REJECT (clearly bad or very high-confidence anomaly).
2. False Positive case — a genuinely healthy part gets wrongly flagged. Cost: an expensive, hard-to-replace good part gets thrown away.
3. False Negative case — a genuinely defective part gets wrongly passed. Cost: possible failure once the part is in space — far more serious than a false positive.
4. Plain "accuracy" as a single number is misleading here, because almost all parts are healthy. A system that always says "normal" would score very high accuracy while catching zero real defects.

**Diagram to make later:** a 2x2 table — Predicted Normal / Predicted Anomalous, against Actually Normal / Actually Defective — with the real-world cost of each of the 4 boxes written in plain words.

---

## PART 10 — Real-World Deployment Constraints (making it actually usable, not just a demo)

**All cases:**
1. Real-time/streaming data case (from Part 3) — the system must work with partial data at each checkpoint, not just a finished table.
2. Dataset mapping/portability case (from Part 3) — the system must not depend on exact column names or units from the training dataset; a configurable mapping layer is needed so it can be reused on a different dataset (like ISRO's real one) without a full rebuild.
3. Threshold recalibration case — values tuned on proxy/public training data (like the contamination value, or drift danger-limits) will almost certainly need to be re-tuned once real data is available; this should be stated honestly, not hidden.
4. Generalization across part types — does the model need separate tuning for each part type (digital vs analog vs power devices), or can one system handle all of them reasonably well?
5. Human-in-the-loop case — REVIEW-tier and RETEST-tier parts need to route to a real QA inspector, who makes the final call; the AI gives a recommendation, not a final decision.
6. Traceability/auditability case — for space-grade QA, every decision needs a documented, defensible reason (this connects back to Part 8's explainability requirement).

---

## Summary table — all 10 parts at a glance

| Part | Name | Number of cases listed |
|---|---|---|
| 1 | The Component | 4 |
| 2 | The Burn-In Test Process | 7 |
| 3 | The Data Being Collected | 5 |
| 4 | Data Quality Problems | 12 |
| 5 | The Core Anomaly/Drift Problem | 17 |
| 6 | Physical Causes of Drift | 6 |
| 7 | Confounders (false alarms) | 6 |
| 8 | The Modeling/Decision-Design Problem | 7 |
| 9 | What "Correct" Looks Like | 4 |
| 10 | Real-World Deployment Constraints | 6 |

**Total: 10 parts, 74 individual cases.** Every case in this table needs its own plain explanation, at least one worked example, and (where marked) a diagram — that is the next step your team does together before moving to literature review and solution design.
