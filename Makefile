# Genome Firewall — one-command pipeline. Activate the conda env first:
#   conda env create -f environment.yml && conda activate genome-firewall && amrfinder --update

PY=python src

.PHONY: all ingest annotate features split train evaluate app api test smoke clean

all: ingest annotate features split train evaluate

ingest:      ## download BV-BRC genomes + lab-measured AMR labels
	$(PY)/ingest_bvbrc.py

smoke:       ## tiny end-to-end run (20 genomes) to validate wiring
	$(PY)/ingest_bvbrc.py --max-genomes 20

annotate:    ## run AMRFinderPlus over all genomes
	$(PY)/annotate.py --workers 4

features:    ## build presence/absence matrix + dictionary
	$(PY)/features.py

split:       ## homology clustering + grouped train/calib/test split
	$(PY)/cluster_split.py

train:       ## per-drug calibrated logistic regression
	$(PY)/train.py

evaluate:    ## held-out metrics + reliability plots -> reports/
	$(PY)/evaluate.py

app:         ## launch the Streamlit decision report
	streamlit run app/streamlit_app.py

api:         ## FastAPI backend for the Svelte UI (http://127.0.0.1:8000)
	python -m uvicorn src.api:app --reload --host 127.0.0.1 --port 8000

api-public:  ## bind 0.0.0.0 for remote clients (EC2 / ngrok / Vercel UI)
	python -m uvicorn src.api:app --host 0.0.0.0 --port 8000

test:        ## unit tests incl. leakage guard
	python -m pytest tests/ -q

clean:
	rm -rf data/interim/* data/processed/* models/*.joblib reports/*.png reports/*.md
