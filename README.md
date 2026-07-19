# 🧬 GenoWall

An AI defense system against superbugs. Given **one reconstructed bacterial genome (FASTA)**,
it predicts — for each of a few antibiotics — whether the drug is **likely to work**,
**likely to fail**, or **no-call**, with a **calibrated confidence**, the **supporting
genes/mutations**, and a mandatory *"confirm with standard lab testing"* message.

**Strictly defensive.** It predicts and explains resistance that already exists. It never
designs, modifies, strengthens, or optimizes an organism.

> Hack-Nation × MIT × OpenAI — Challenge 06. This is a research prototype, not a clinical tool.

---

## What's here (the 3 required modules)

| Module | Files | Does |
|---|---|---|
| **01 Genome Reader** | `src/ingest_bvbrc.py`, `src/annotate.py`, `src/features.py` | FASTA → AMRFinderPlus → presence/absence feature matrix (+ dictionary of known mechanisms) |
| **02 Predictor** | `src/cluster_split.py`, `src/target_gate.py`, `src/train.py` | homology-grouped split • drug-target gate • per-drug **calibrated** logistic regression |
| **03 Decision Report** | `src/nocall.py`, `src/explain.py`, `src/predict.py`, `src/evaluate.py`, `src/api.py`, `app/streamlit_app.py`, **`ui/`** | no-call logic • honest evidence • FastAPI + Streamlit + **Svelte UI** |

## Quickstart

```bash
# 1. environment (installs AMRFinderPlus, mash, cd-hit, sklearn, streamlit ...)
conda env create -f environment.yml
conda activate genowall
amrfinder --update          # one-time: download the AMR database

# 2. full pipeline (edit config.yaml first: species + antibiotics)
make smoke                  # tiny 20-genome wiring test, OR:
make all                    # ingest -> annotate -> features -> split -> train -> evaluate

# 3. demo
make app                    # Streamlit decision report
make api                    # FastAPI for the Svelte UI (port 8000)
make test                   # unit tests incl. the leakage guard

# 4. Svelte UI (same repo, folder ui/)
cd ui && cp .env.example .env.local && npm install && npm run dev
```

`POST /predict` accepts a FASTA upload and returns the same JSON as `predict_report()`.

### Deploy (hackathon) — one GitHub repo

Import **`eylernur/genowall`** on Vercel. In **Project Settings → General**:

- **Framework Preset:** Vite (not FastAPI)
- **Root Directory:** `ui`  ← important, or Vercel will try to deploy `src/api.py` as Python

| Piece | Where | Notes |
|-------|--------|--------|
| **UI** | **Vercel** ← this repo | Static Vite app in `ui/` |
| **API** | Laptop + ngrok, or EC2 | Not Vercel — needs AMRFinder (~1–2 min/genome) |

```bash
# public API for the live Vercel site
make api-public
ngrok http 8000
# Vercel → Settings → Environment Variables → VITE_API_URL=https://….ngrok-free.app → Redeploy
```

Without `VITE_API_URL`, the Vercel site still loads in **mock demo** mode.

## Configuration

Everything is driven by `config.yaml`: species, antibiotic list, feature thresholds,
homology threshold, calibration method, and the no-call bands. Change scope there.

## Module 01 output-format spec (graded "Required")

`data/processed/features.parquet`:
- index `genome_id` (str); one **binary** column per AMR feature.
- feature name = `"<Element subtype>:<Gene symbol>"` (e.g. `AMR:blaKPC-2`, `POINT:gyrA_S83L`).
- value `1` iff AMRFinderPlus reported it with `%identity ≥ min_identity` AND
  `%coverage ≥ min_coverage` (from `config.features`).

`data/processed/feature_dictionary.csv`: each feature tagged with drug class + a
`known_mechanism` flag (used to separate **biological** evidence from **statistical** ones).

## How each Responsibility Requirement is met

1. **Defensive by construction** — read-only prediction of existing resistance; no design path anywhere. Banner + note in the app.
2. **Honest generalization** — `cluster_split.py` groups genomes by Mash homology and splits by cluster; `evaluate.py` reports per genetic group. `test_leakage.py` fails the build if a cluster leaks across splits.
3. **Calibrated confidence + no-call** — `train.py` calibrates on a held-out split; `evaluate.py` reports Brier + reliability plots; `nocall.py` abstains on weak/conflicting/OOD evidence.
4. **Honest explanations** — `explain.py` labels evidence as *known mechanism* vs *statistical association only*; feature importance is never presented as biological proof.
5. **Human oversight** — every report carries the mandatory lab-confirmation banner; decision support only.

## Data sources (real, open)

- **BV-BRC** genomes + lab-measured AMR phenotypes — https://www.bv-brc.org/docs/quick_references/ftp.html
- **AMRFinderPlus** (NCBI, public domain) — https://github.com/ncbi/amr/wiki
- Optional DL stretch: HyenaDNA / DNABERT-2 on Hugging Face (see `../GENOWALL_BUILD_PLAN.md`).

See `../GENOWALL_BUILD_PLAN.md` for the full spec, phases, and Codex prompts.

## Metrics reported (judging)

Balanced accuracy; recall for resistant & susceptible (separately); F1, AUROC, PR-AUC per
drug; Brier score + reliability plot; no-call rate + accuracy on remaining calls;
per-genetic-group breakdown on held-out data.
