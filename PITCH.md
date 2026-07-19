# Genome Firewall — Pitch

## 1. One-line hook

Upload one bacterial genome. Get a per-antibiotic **work / fail / no-call** — with calibrated confidence and honest evidence — before the culture result comes back.

## 2. The problem

Doctors start antibiotics before the lab can answer.

- Phenotypic susceptibility testing takes **1–3 days**.
- In that window, care is empiric — and roughly **~20% of empiric therapy is wrong**.
- In many LMIC settings, susceptibility testing is scarce or never done, so broad-spectrum drugs are over-prescribed and resistance spreads faster.

The genome already holds resistance clues. The bottleneck is turning that DNA into a trustworthy, auditable call.

## 3. Our solution

**Genome Firewall** takes a reconstructed genome **FASTA** and returns, for each antibiotic in scope:

- **Likely to work** / **likely to fail** / **no-call**
- A **calibrated confidence** score
- **Evidence**: known resistance gene/mutation, statistical association only, or no signal
- A mandatory *confirm with standard lab testing* message

Strictly defensive: we predict and explain resistance that already exists. We never design, modify, strengthen, or optimize an organism.

`[RESULTS]` — insert headline held-out metrics here (balanced accuracy, Brier / calibration, no-call rate, per-group generalization).

## 4. How it works

Three modules, plain language:

1. **01 Genome Reader** — FASTA → AMRFinderPlus → a presence/absence feature matrix of known AMR genes and resistance mutations, plus a dictionary that tags which features are known mechanisms.
2. **02 Predictor** — Homology-grouped train/test split (so near-identical genomes do not leak), a deterministic **drug-target gate**, and a per-drug **calibrated** model that scores work vs fail.
3. **03 Decision Report** — No-call when evidence is weak, conflicting, or out-of-distribution; honest evidence categories; Streamlit report with reliability views and the lab-confirmation banner.

FASTA in → per-drug decision + calibrated confidence + evidence out.

## 5. How we meet all 5 Responsibility Requirements

| Requirement | How we meet it |
|---|---|
| **1. Defensive-only** | Read-only prediction of existing resistance. No design, edit, or optimization path anywhere — defensive by construction, stated in the app. |
| **2. Honest generalization** | Genomes are clustered by Mash homology and split **by cluster**. Evaluation reports per genetic group; a leakage test fails the build if a cluster appears in more than one split. |
| **3. Calibration + no-call** | Models are calibrated on a held-out split; we report Brier + reliability plots. When confidence is weak, signals conflict, or the genome looks OOD, we **abstain (no-call)** instead of forcing a guess. |
| **4. Honest evidence (gene vs statistic)** | Evidence is labeled *known mechanism* vs *statistical association only* vs *no signal*. Feature importance is never sold as biological proof. |
| **5. Human oversight** | Decision support only. Every report carries the mandatory lab-confirmation banner; a clinician/lab confirms with standard testing. |

## 6. Why it matters

AMR already kills at massive scale: on the order of **~4.7 million deaths per year associated with AMR**, and **more than 1 million directly attributable**. Faster, more honest genome-informed guidance — especially where culture labs are slow or unavailable — can cut wrong first courses and slow resistance selection.

## 7. Honest limitations

- **One species** in this prototype (*Klebsiella pneumoniae*)
- **Few drugs** (focused panel — e.g. ciprofloxacin, gentamicin, meropenem, ceftazidime)
- **Research prototype** — Hack-Nation × MIT × OpenAI Challenge 06; not a clinical IVD
- **Confirm with lab testing** — phenotypic AST remains the ground truth for definitive therapy

`[RESULTS]` — final demo numbers (accuracy, calibration, no-call rate, per-group table) go here.
