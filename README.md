# 🧬 Genome Firewall

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
| **03 Decision Report** | `src/nocall.py`, `src/explain.py`, `src/predict.py`, `src/evaluate.py`, `src/api.py`, `app/streamlit_app.py` | no-call logic • honest evidence • FastAPI + Streamlit • held-out metrics |

## Quickstart

```bash
# 1. environment (installs AMRFinderPlus, mash, cd-hit, sklearn, streamlit ...)
conda env create -f environment.yml
conda activate genome-firewall
amrfinder --update          # one-time: download the AMR database

# 2. full pipeline (edit config.yaml first: species + antibiotics)
make smoke                  # tiny 20-genome wiring test, OR:
make all                    # ingest -> annotate -> features -> split -> train -> evaluate

# 3. demo (either UI)
make app                    # Streamlit decision report
make api                    # FastAPI for the sibling Svelte UI (port 8000)
make test                   # unit tests incl. the leakage guard
```

### Svelte UI (sibling repo)

The frontend lives next to this repo as [`genome-firewall-ui`](https://github.com/eylernur/genome-firewall-ui):

```bash
# terminal A — this repo
conda activate genome-firewall
make api

# terminal B — UI
cd ../genome-firewall-ui
cp .env.example .env.local   # VITE_API_URL=http://127.0.0.1:8000
npm install && npm run dev
```

`POST /predict` accepts a FASTA upload and returns the same JSON as `predict_report()`.

### Deploy (hackathon)

- **UI → Vercel** (static Vite build). Set env `VITE_API_URL` to your public API base.
- **API → not Vercel.** Predictions need AMRFinder + conda + ~1–2 min CPU. Run on a laptop (`make api-public` + [ngrok](https://ngrok.com) for HTTPS) or EC2/VM with HTTPS.
- Browser calls the API **directly** (CORS is open). Vercel HTTPS pages require an **HTTPS** API URL (mixed content otherwise).

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
- Optional DL stretch: HyenaDNA / DNABERT-2 on Hugging Face (see `GENOME_FIREWALL_BUILD_PLAN.md`).

See `../GENOME_FIREWALL_BUILD_PLAN.md` for the full spec, phases, and Codex prompts.

## Metrics reported (judging)

Balanced accuracy; recall for resistant & susceptible (separately); F1, AUROC, PR-AUC per
drug; Brier score + reliability plot; no-call rate + accuracy on remaining calls;
per-genetic-group breakdown on held-out data.
