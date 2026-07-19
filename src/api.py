"""FastAPI backend for Genome Firewall.

Exposes the existing predict_report() pipeline over HTTP so a separate frontend
(SvelteKit / React) can call it. Does NOT change any modeling code.

Run:
    conda activate genome-firewall
    python -m uvicorn src.api:app --reload --host 127.0.0.1 --port 8000
    # or: make api

Endpoints:
    GET  /health        -> {"status":"ok", ...scope}
    GET  /metrics       -> held-out metrics summary (from reports/metrics.md if present)
    POST /predict       -> multipart file upload (FASTA) -> full antibiotic-response JSON
"""
from __future__ import annotations
import sys
import tempfile
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from utils import load_config  # noqa: E402
from predict import predict_report  # noqa: E402

cfg = load_config()
app = FastAPI(title="Genome Firewall API", version="1.0")

# allow the frontend dev server (Svelte/Vite default ports) to call us
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],           # tighten to your frontend origin in production
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "species": cfg["species"]["name"],
        "antibiotics": cfg["antibiotics"],
        "lab_banner": cfg["report"]["lab_banner"],
        "defensive_note": cfg["report"]["defensive_note"],
    }


@app.get("/metrics")
def metrics():
    p = ROOT / "reports" / "metrics.md"
    return {"metrics_markdown": p.read_text() if p.exists() else "No metrics yet."}


@app.post("/predict")
async def predict(file: UploadFile = File(...)):
    name = file.filename or "genome.fna"
    if not name.lower().endswith((".fna", ".fasta", ".fa", ".txt")):
        raise HTTPException(400, "Upload a FASTA file (.fna/.fasta/.fa).")
    data = await file.read()
    with tempfile.NamedTemporaryFile(suffix=".fna", delete=False) as tmp:
        tmp.write(data)
        fna_path = tmp.name
    try:
        report = predict_report(fna_path, cfg)
    except FileNotFoundError:
        raise HTTPException(500, "AMRFinderPlus not found on server. Activate env + amrfinder --update.")
    except Exception as e:  # noqa: BLE001
        raise HTTPException(500, f"Prediction failed: {e}")
    report["genome_id"] = name.rsplit(".", 1)[0]
    return report
