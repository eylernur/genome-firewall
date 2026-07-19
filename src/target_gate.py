"""Module 02: deterministic drug-target gate.

Rule from the brief: do NOT report "likely to work" based solely on the absence of
resistance markers. A drug can only work if its molecular target is present/intact.

This gate reads drugs.csv (antibiotic -> target genes) and the per-genome AMR features
(+ optionally a core-gene presence check) and returns, per (genome, drug):
    "target_present" | "target_absent" | "unknown"

Interpretation used downstream (nocall.py):
  - target_absent  -> the drug's binding site is missing/disrupted; a naive "works"
                      call is unsafe -> push to no-call (or "fail" per your rule).
  - target_present -> normal model prediction applies.

NOTE (honesty): most essential targets (gyrA, PBPs, ribosome) are always present in a
viable genome, so the common, meaningful signal here is a *disrupted/lost* target
(e.g. ompK porin loss for carbapenems is handled as a resistance feature, not a target
loss). Keep the gate conservative and documented; log every time it fires.
"""
from __future__ import annotations
import pandas as pd

from utils import load_config, resolve, normalize_drug, get_logger

log = get_logger("gate")


def load_drug_targets(cfg: dict) -> dict[str, list[str]]:
    drugs = pd.read_csv(resolve(cfg["paths"]["drugs_csv"]))
    out = {}
    for _, r in drugs.iterrows():
        ab = normalize_drug(r["antibiotic"])
        targets = [t.strip() for t in str(r["molecular_target_genes"]).split(";") if t.strip()]
        out[ab] = targets
    return out


def gate_for_genome(features_row: pd.Series, drug: str, targets: dict[str, list[str]]) -> str:
    """features_row: binary AMR features for one genome (index = feature names).

    Because AMRFinderPlus reports resistance determinants (not housekeeping genes),
    presence of a target gene is generally assumed for a viable isolate. We flag
    'target_absent' only when a target-disrupting feature is present (extend as needed).
    """
    tlist = targets.get(normalize_drug(drug), [])
    if not tlist:
        return "unknown"
    # Look for explicit target-loss / disruption signals in the feature names.
    present_feats = {f.split(":")[-1].lower() for f, v in features_row.items() if v == 1}
    disruptors = {"ompk35", "ompk36", "porin_loss"}  # example carbapenem porin losses
    if present_feats & disruptors and normalize_drug(drug) in {"meropenem", "ceftazidime"}:
        return "target_absent"   # porin loss reduces drug entry -> treat as gate-relevant
    return "target_present"


def gate_all(features: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    targets = load_drug_targets(cfg)
    rows = []
    for gid, row in features.iterrows():
        for drug in cfg["antibiotics"]:
            rows.append({"genome_id": gid, "antibiotic": normalize_drug(drug),
                         "gate": gate_for_genome(row, drug, targets)})
    return pd.DataFrame(rows)


if __name__ == "__main__":
    cfg = load_config()
    feats = pd.read_parquet(resolve(cfg["features"]["matrix_path"]))
    g = gate_all(feats, cfg)
    log.info("gate distribution:\n%s", g["gate"].value_counts().to_string())
