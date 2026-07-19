"""End-to-end inference: one FASTA -> full antibiotic-response report (JSON).

Pipeline: FASTA -> AMRFinderPlus -> feature vector (aligned to training columns)
       -> per-drug calibrated model -> target gate -> no-call logic -> evidence.

Used by both the CLI and the Streamlit app.
"""
from __future__ import annotations
import argparse
import json
import subprocess
import tempfile
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from utils import load_config, resolve, get_logger, normalize_drug
from target_gate import load_drug_targets, gate_for_genome
from nocall import decide
from explain import (evidence_for, top_features_for_drug, drug_class_features, maybe_llm_prose)

log = get_logger("predict")

# drug -> keywords used to match a curated feature's AMRFinderPlus "Class" to the drug
DRUG_CLASS_KEYWORDS = {
    "ciprofloxacin": ["quinolone", "fluoroquinolone"],
    "gentamicin": ["aminoglycoside"],
    "meropenem": ["carbapenem", "beta-lactam"],
    "ceftazidime": ["cephalosporin", "beta-lactam"],
    "trimethoprim/sulfamethoxazole": ["trimethoprim", "sulfonamide", "folate"],
}


def run_amrfinder(fna_path: str, organism: str) -> pd.DataFrame:
    with tempfile.NamedTemporaryFile(suffix=".tsv", delete=False) as tmp:
        out = tmp.name
    cmd = ["amrfinder", "-n", fna_path, "--plus", "-o", out]
    if organism:
        cmd += ["--organism", organism]
    subprocess.run(cmd, check=True, capture_output=True, text=True)
    df = pd.read_csv(out, sep="\t", dtype=str)
    df.columns = [c.strip() for c in df.columns]
    # normalize AMRFinderPlus column names across versions (old + new)
    aliases = {
        "Gene symbol": "Gene symbol", "Element symbol": "Gene symbol",
        "Element subtype": "Element subtype", "Subtype": "Element subtype",
        "% Identity to reference sequence": "% Identity", "% Identity to reference": "% Identity",
        "% Coverage of reference sequence": "% Coverage", "% Coverage of reference": "% Coverage",
    }
    return df.rename(columns=aliases)


def featurize(amr_df: pd.DataFrame, feature_cols: list[str], cfg: dict) -> pd.Series:
    fcfg = cfg["features"]
    active = {}
    for _, r in amr_df.iterrows():
        subtype = str(r.get("Element subtype", "AMR")).upper()
        gene = str(r.get("Gene symbol", "")).strip()
        if not gene:
            continue
        try:
            idv = float(r.get("% Identity", 100) or 100)
            cov = float(r.get("% Coverage", 100) or 100)
        except ValueError:
            idv = cov = 100.0
        if idv >= fcfg["min_identity"] and cov >= fcfg["min_coverage"]:
            active[f"{subtype}:{gene}"] = 1
    vec = pd.Series(0, index=feature_cols, dtype=int)
    for f in active:
        if f in vec.index:
            vec[f] = 1
    return vec


def predict_report(fna_path: str, cfg: dict, ood_similarity: float | None = None) -> dict:
    proc = resolve(cfg["paths"]["processed_dir"])
    dictionary = pd.read_csv(resolve(cfg["features"]["dictionary_path"])) \
        if resolve(cfg["features"]["dictionary_path"]).exists() else pd.DataFrame()
    targets = load_drug_targets(cfg)

    amr_df = run_amrfinder(fna_path, cfg["species"]["amrfinder_organism"])

    results = []
    for drug in [normalize_drug(d) for d in cfg["antibiotics"]]:
        model_path = resolve(cfg["model"]["models_dir"]) / f"{drug.replace('/', '_')}.joblib"
        if not model_path.exists():
            results.append({"antibiotic": drug, "call": "no-call",
                            "reason": "no trained model for this drug", "confidence": None})
            continue
        bundle = joblib.load(model_path)
        vec = featurize(amr_df, bundle["features"], cfg)
        X = vec.to_frame().T

        est = bundle["calibrator"] or bundle["pipeline"]
        prob_fail = float(est.predict_proba(X)[0][1])

        gate = gate_for_genome(vec, drug, targets)
        call = decide(prob_fail, gate, ood_similarity, cfg)

        active = [f for f, v in vec.items() if v == 1]
        class_feats = drug_class_features(dictionary, DRUG_CLASS_KEYWORDS.get(drug, []))
        top = top_features_for_drug(bundle)
        ev = evidence_for(call["call"], active, class_feats, top, drug)
        prose = maybe_llm_prose({**call, **ev, "antibiotic": drug}, cfg)

        results.append({
            "antibiotic": drug,
            "call": call["call"],
            "prob_fail": round(prob_fail, 3),
            "confidence": call["confidence"],
            "gate": gate,
            "evidence_type": ev["evidence_type"],
            "detected_genes": ev["detected_genes"],
            "statistical_features": ev["statistical_features"],
            "note": ev["note"],
            "nocall_reason": call["reason"],
            "prose": prose,
        })

    return {
        "species": cfg["species"]["name"],
        "results": results,
        "coverage_note": f"Covers {cfg['species']['name']} and {len(cfg['antibiotics'])} "
                         f"antibiotics only.",
        "lab_banner": cfg["report"]["lab_banner"],
        "defensive_note": cfg["report"]["defensive_note"],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("fasta", help="path to a genome .fna/.fasta")
    ap.add_argument("--config", default=None)
    args = ap.parse_args()
    cfg = load_config(args.config)
    report = predict_report(args.fasta, cfg)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
