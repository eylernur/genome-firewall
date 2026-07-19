# SETUP — first-time walkthrough

Use the folder **`genowall`** (this repo). Open it in Cursor/VS Code and run commands in that terminal.

---

## 1. Install conda (if needed)

```bash
conda --version
```

If missing, install [Miniforge](https://github.com/conda-forge/miniforge), reopen the terminal, check again.

---

## 2. Create the environment (one time, ~5–15 min)

```bash
conda env create -f environment.yml
conda activate genowall
amrfinder --update
```

Installs AMRFinderPlus, mash, scikit-learn, FastAPI, Streamlit, etc.

---

## 3. Run with shipped models (fastest)

Models are already in `models/`. You only need the API + UI:

```bash
# terminal 1
conda activate genowall
make api

# terminal 2
cd ui
cp .env.example .env.local
npm install
npm run dev
```

Browser → http://127.0.0.1:5173 → upload a FASTA.

---

## 4. Optional — tiny pipeline smoke test

```bash
conda activate genowall
make smoke
```

Downloads ~20 genomes. If it finishes without a red error, ingest wiring works.

---

## 5. Optional — full retrain

```bash
make all
```

Order: ingest → annotate → features → split → train → evaluate.  
Can take many hours. Results → `reports/metrics.md`.

Edit `config.yaml` first if you change species or drugs.

---

## 6. Optional — Streamlit instead of Svelte

```bash
make app
```

---

## 7. Checks

```bash
make test
```

Includes a leakage guard (clusters must not appear in more than one split).

---

## Common issues

- **`make` missing on Mac:** `xcode-select --install`, or run the `python src/...` commands from the Makefile by hand.
- **Wrong conda env:** always `conda activate genowall` (not the old `genome-firewall` name).
- **Vercel:** Root Directory = `ui`, Framework = Vite. See main README.

Full product docs: [README.md](README.md)
