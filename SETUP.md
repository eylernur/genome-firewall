# START HERE — do this top to bottom

**The only folder you use:** `Genome firewall/genome-firewall`
Everything lives here. Open THIS folder in Cursor and never leave it.

---

## Step 1 — Open the project in Cursor
Cursor → File → Open Folder → choose:
`Downloads/Genome firewall/genome-firewall`

Open the terminal inside Cursor: menu **Terminal → New Terminal**.
Every command below goes in that terminal.

---

## Step 2 — Install conda (only if you don't have it)
Check first:
```
conda --version
```
If it says "command not found", install Miniforge (Mac):
```
curl -L -O https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-MacOSX-arm64.sh
bash Miniforge3-MacOSX-arm64.sh
```
Close and reopen the terminal, then run `conda --version` again to confirm.

---

## Step 3 — Build the environment (one time, ~5 min)
```
conda env create -f environment.yml
conda activate genome-firewall
amrfinder --update
```
This installs AMRFinderPlus, mash, cd-hit, scikit-learn, streamlit — all of it.

---

## Step 4 — Add your OpenAI key (optional, for the explanation text)
```
export OPENAI_API_KEY=sk-your-key-here
```
Then open `config.yaml` and set `llm: enabled: true`.
Skip this step entirely if you just want the core predictions working first.

---

## Step 5 — Test the wiring with a tiny run
```
make smoke
```
This downloads ~20 genomes and runs part of the pipeline. If it finishes without
a red error, the plumbing works.

> If `make` isn't found on Mac: run `xcode-select --install`, or just run the
> commands inside the Makefile directly (e.g. `python src/ingest_bvbrc.py --max-genomes 20`).

---

## Step 6 — Run the full pipeline
```
make all
```
Order it runs: ingest → annotate → features → split → train → evaluate.
Results land in `reports/metrics.md` and `reports/reliability_*.png`.

---

## Step 7 — Launch the demo app
```
make app
```
A browser tab opens. Upload a genome FASTA → see the antibiotic report.

---

## Step 8 — Check your work
```
make test
```

---

## If something breaks
Paste the error into Cursor's chat (Agent mode) and say:
"Fix this. Context: GENOME_FIREWALL_BUILD_PLAN.md and README.md."
Use **Composer 2.5** for small fixes, switch to **Claude Opus / GPT-Codex** for hard ones.

## The two things to sanity-check on first run
1. `make ingest` — confirm the BV-BRC column names match those in `src/ingest_bvbrc.py`.
2. After `make annotate` — confirm AMRFinderPlus TSV columns match `src/features.py`.
Cursor can reconcile both in 2 minutes if they differ.

---

That's the whole thing. One folder, eight steps.
