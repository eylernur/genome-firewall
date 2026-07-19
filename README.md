# GenoWall

**Genomic antibiotic resistance prediction — with calibrated confidence — before culture results arrive.**

Upload one reconstructed bacterial genome (FASTA). GenoWall returns, for each antibiotic in scope:

| Call | Meaning |
|------|---------|
| **Likely to work** | Drug predicted effective |
| **Likely to fail** | Resistance predicted |
| **No-call** | Evidence too weak / conflicting / out-of-distribution — abstain |

Plus calibrated confidence, known resistance genes vs statistical associations only, a recommended empiric choice, PDF download, and share.

> **Research prototype — not for clinical use.** Confirm every result with standard laboratory testing.  
> **Defensive only:** predicts and explains resistance that already exists. Never designs, modifies, or optimizes organisms.

Hack-Nation × MIT × OpenAI — Challenge 06 · Built by [Eyler Nur](https://github.com/eylernur)

---

## Who is this for?

| You want to… | Start here |
|--------------|------------|
| **Try the product UI** | [Quick start — UI + API](#quick-start--use-the-app-5-minutes-if-models-exist) |
| **Retrain / reproduce metrics** | [How training works](#how-training-works) + [Full pipeline](#full-pipeline--train-from-scratch) |
| **Deploy the website** | [Deploy](#deploy) |
| **Understand the science / responsibility** | [Architecture](#architecture) + [Responsibility requirements](#responsibility-requirements) |

Trained models and held-out metrics ship in this repo (`models/`, `reports/`), so you can **run predictions without re-downloading thousands of genomes**.

---

## What’s in the box

```
genowall/
├── ui/                 # Svelte landing page + clinical report (Vercel)
├── src/                # Python: ingest → annotate → features → train → predict → API
├── app/                # Optional Streamlit report
├── models/             # Trained per-drug calibrated models (*.joblib)
├── data/processed/     # Feature matrix, labels, splits, dictionary
├── reports/            # metrics.md + reliability plots
├── config.yaml         # Species, drugs, thresholds — edit this to change scope
├── drugs.csv           # Drug → molecular target genes (target gate)
└── environment.yml     # Conda env (AMRFinderPlus, mash, sklearn, FastAPI, …)
```

**Scope (default):** *Klebsiella pneumoniae* · ciprofloxacin · gentamicin · meropenem · ceftazidime

**Held-out (homology-grouped test):** balanced accuracy ≈ **0.90–0.94** · AUROC ≈ **0.94–0.98** · Brier ≈ **0.04–0.05** — see [`reports/metrics.md`](reports/metrics.md).

---

## Quick start — use the app (5 minutes if models exist)

### 1. Requirements

- macOS / Linux
- [Conda / Miniforge](https://github.com/conda-forge/miniforge)
- Node.js 20+ (for the UI)
- ~5 GB free for the AMRFinder database (one-time)

### 2. Install

```bash
git clone https://github.com/eylernur/genowall.git
cd genowall

conda env create -f environment.yml
conda activate genowall
amrfinder --update          # one-time NCBI AMR database download
```

### 3. Start the API

```bash
make api
# → http://127.0.0.1:8000/health
# → POST http://127.0.0.1:8000/predict  (multipart field: file)
```

### 4. Start the UI

```bash
cd ui
cp .env.example .env.local   # VITE_API_URL=http://127.0.0.1:8000
npm install
npm run dev
# → http://127.0.0.1:5173
```

Upload a quality-checked `.fna` / `.fasta` (e.g. BV-BRC *K. pneumoniae*).  
Expect **~1–2 minutes** per genome (AMRFinderPlus). You’ll get a recommendation, per-drug cards, **Download PDF**, and **Share**.

**Optional Streamlit UI:** `make app` (same models, different front-end).

**Tests:** `make test` (includes a train/test leakage guard).

---

## How training works

Plain-language overview of what `make all` does:

```
BV-BRC genomes + lab AST labels
        │
        ▼
 ① Annotate each genome with AMRFinderPlus
        │  (known AMR genes & point mutations)
        ▼
 ② Build a presence/absence feature matrix
        │
        ▼
 ③ Cluster genomes by Mash homology
        │  (near-identical genomes stay in the SAME split)
        ▼
 ④ Train / calibration / test split by cluster
        │
        ▼
 ⑤ Per-drug logistic regression + calibration
        │  + drug-target gate
        ▼
 ⑥ Evaluate on held-out clusters → reports/
        │
        ▼
 ⑦ At inference: annotate → score → no-call rules → report
```

### Step by step

1. **Ingest** (`src/ingest_bvbrc.py`)  
   Downloads *K. pneumoniae* genomes and **lab-measured** phenotypes only (MIC / disk / VITEK / …). Computational “predictions” as labels are dropped.

2. **Annotate** (`src/annotate.py`)  
   Runs **AMRFinderPlus** per genome → interim TSV hits (resumable, multi-worker).

3. **Features** (`src/features.py`)  
   Binary matrix: feature = `Subtype:Gene` (e.g. `AMR:blaKPC-2`, `POINT:gyrA_S83I`) if identity & coverage ≥ thresholds in `config.yaml`.  
   A **feature dictionary** marks known mechanisms vs statistical-only features.

4. **Honest split** (`src/cluster_split.py`)  
   Genomes clustered with **Mash**; clusters are never split across train / calib / test. This prevents near-duplicate leakage.

5. **Train** (`src/train.py`)  
   One **balanced L2 logistic regression** per antibiotic, then **probability calibration** (isotonic or Platt) on the calibration split.  
   A **drug-target gate** checks whether the molecular target genes look intact.

6. **No-call** (`src/nocall.py`)  
   Abstain when calibrated probability is in an uncertain band, evidence conflicts with the gate, or the genome looks out-of-distribution vs training clusters.

7. **Explain** (`src/explain.py`)  
   Labels evidence as *known resistance mechanism* vs *statistical association only* vs *no known signal*.

8. **Evaluate** (`src/evaluate.py`)  
   Held-out metrics + reliability plots → `reports/`.

**You do not need to retrain** to use the shipped `models/*.joblib`. Retrain when you change species, drugs, or data.

---

## Full pipeline — train from scratch

> Warning: full ingest + annotate over thousands of genomes needs disk, network, and many hours of CPU.

```bash
conda activate genowall

# Tiny wiring test (~20 genomes)
make smoke

# Full run: ingest → annotate → features → split → train → evaluate
make all

# Or step by step:
make ingest
make annotate      # use: python src/annotate.py --workers 6
make features
make split
make train
make evaluate
```

Edit **`config.yaml`** before training to change species, antibiotic list, Mash threshold, calibration, or no-call bands.

Artifacts:

| Path | Purpose |
|------|---------|
| `data/processed/features.parquet` | Feature matrix |
| `data/processed/labels.parquet` | Lab labels |
| `data/processed/splits.json` | Homology-grouped splits |
| `models/<drug>.joblib` | Calibrated models |
| `reports/metrics.md` | Held-out table |
| `reports/reliability_*.png` | Calibration plots |

---

## API reference

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Species, antibiotics, banners |
| `GET` | `/metrics` | Contents of `reports/metrics.md` |
| `POST` | `/predict` | `multipart/form-data` field `file` = FASTA → JSON report |

```bash
curl -s http://127.0.0.1:8000/health
curl -s -X POST -F "file=@genome.fna" http://127.0.0.1:8000/predict | jq .
```

Public bind (ngrok / LAN): `make api-public`

---

## Deploy

### UI → Vercel (this repo)

1. Import **`eylernur/genowall`**
2. **Root Directory:** `ui`
3. **Framework:** Vite  
4. Leave install/build/output blank (see `ui/vercel.json`)
5. Optional env: `VITE_API_URL` = your public **HTTPS** API base

Without `VITE_API_URL`, the site runs in **preview/mock** mode (UI only).

### API → not Vercel

Predictions need AMRFinder + conda (~1–2 min/genome). Run on a laptop or VM:

```bash
make api-public
ngrok http 8000
# set Vercel VITE_API_URL=https://xxxx.ngrok-free.app → Redeploy
```

Vercel is HTTPS → the API URL must be HTTPS too (mixed content otherwise).

---

## Architecture

| Module | Code | Role |
|--------|------|------|
| **01 Genome Reader** | `ingest_bvbrc.py`, `annotate.py`, `features.py` | FASTA → AMR features |
| **02 Predictor** | `cluster_split.py`, `target_gate.py`, `train.py` | Honest split + calibrated models |
| **03 Decision Report** | `nocall.py`, `explain.py`, `predict.py`, `api.py`, `ui/` | No-call, evidence, FastAPI, Svelte UI |

```
Browser (ui/) ──POST FASTA──► FastAPI (src/api.py) ──► predict_report()
                                                         ├─ AMRFinderPlus
                                                         ├─ calibrated models
                                                         └─ no-call + evidence
```

---

## Responsibility requirements

1. **Defensive by construction** — read-only resistance prediction; no design path.  
2. **Honest generalization** — Mash homology-grouped splits + leakage test.  
3. **Calibration + no-call** — calibrated probs, Brier/reliability, abstain when unsure.  
4. **Honest evidence** — gene/mechanism vs statistical association only.  
5. **Human oversight** — lab-confirmation banner; decision support only.

---

## Data sources

- [BV-BRC](https://www.bvbrc.org/) — genomes + lab AMR phenotypes  
- [AMRFinderPlus](https://github.com/ncbi/amr/wiki) — NCBI resistance annotation  

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `amrfinder: command not found` | `conda activate genowall` then `amrfinder --update` |
| UI upload does nothing / API errors | Ensure `make api` is running; check `ui/.env.local` |
| Vercel builds FastAPI / Python error | Set **Root Directory = `ui`**, Framework = Vite |
| `npm ci --prefix ui` fails on Vercel | Don’t use `--prefix` when Root Directory is already `ui` |
| Predict takes forever | Normal: AMRFinder ~1–2 min/genome |
| Want a different species/drug | Edit `config.yaml` + `drugs.csv`, then re-run pipeline |

More hand-holding: see [`SETUP.md`](SETUP.md).

---

## License & disclaimer

Code is released under the [MIT License](LICENSE).

Research / educational prototype for the Hack-Nation challenge.  
**Not a medical device. Not for patient care.** Always confirm with standard AST.
