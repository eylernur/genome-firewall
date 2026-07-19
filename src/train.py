"""Module 02: one calibrated regularized logistic-regression model per antibiotic.

- Fit L2 logistic regression on the TRAIN genomes (features from Module 01).
- Calibrate probabilities on the separate CALIB split (isotonic if enough data, else Platt).
- Save {drug: model+calibrator} to models/.

Saved per drug: models/<drug>.joblib  containing:
  { "pipeline": sklearn estimator, "calibrator": CalibratedClassifierCV or None,
    "features": [col order], "train_prevalence": float }
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from utils import load_config, resolve, get_logger, normalize_drug

log = get_logger("train")


def _xy(features: pd.DataFrame, labels: pd.DataFrame, ids: list[str], drug: str):
    sub = labels[(labels["antibiotic"] == drug) & (labels["genome_id"].isin(ids))]
    sub = sub[sub["genome_id"].isin(features.index)]
    X = features.loc[sub["genome_id"]]
    y = sub["label"].to_numpy()
    return X, y, sub["genome_id"].tolist()


def train_drug(features, labels, splits, drug, cfg):
    from sklearn.linear_model import LogisticRegression
    from sklearn.calibration import CalibratedClassifierCV

    mcfg = cfg["model"]
    Xtr, ytr, _ = _xy(features, labels, splits["train"], drug)
    Xca, yca, _ = _xy(features, labels, splits["calib"], drug)

    if len(np.unique(ytr)) < 2:
        log.warning("[%s] only one class in train (n=%d) — skipping.", drug, len(ytr))
        return None

    clf = LogisticRegression(
        penalty=mcfg["penalty"], C=mcfg["C"], class_weight=mcfg["class_weight"],
        max_iter=2000, solver="liblinear",
    )
    clf.fit(Xtr, ytr)

    calibrator = None
    if len(yca) >= 30 and len(np.unique(yca)) == 2:
        method = mcfg["calibration"]
        if method == "auto":
            method = "isotonic" if len(yca) >= 200 else "sigmoid"
        # sklearn >=1.6 deprecates cv="prefit" in favor of FrozenEstimator; support both.
        try:
            from sklearn.frozen import FrozenEstimator
            calibrator = CalibratedClassifierCV(FrozenEstimator(clf), method=method)
        except ImportError:
            calibrator = CalibratedClassifierCV(clf, method=method, cv="prefit")
        calibrator.fit(Xca, yca)
    else:
        log.warning("[%s] calib set too small (n=%d) — using raw probabilities.", drug, len(yca))

    bundle = {
        "pipeline": clf,
        "calibrator": calibrator,
        "features": list(features.columns),
        "train_prevalence": float(np.mean(ytr)),
        "n_train": int(len(ytr)),
        "n_calib": int(len(yca)),
    }
    out = resolve(cfg["model"]["models_dir"]) / f"{drug.replace('/', '_')}.joblib"
    joblib.dump(bundle, out)
    log.info("[%s] trained (n_train=%d, n_calib=%d) -> %s", drug, len(ytr), len(yca), out.name)
    return bundle


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=None)
    args = ap.parse_args()
    cfg = load_config(args.config)

    proc = resolve(cfg["paths"]["processed_dir"])
    features = pd.read_parquet(resolve(cfg["features"]["matrix_path"]))
    labels = pd.read_parquet(proc / "labels.parquet")
    labels["antibiotic"] = labels["antibiotic"].apply(normalize_drug)
    splits = json.loads(resolve(cfg["split"]["splits_path"]).read_text())

    for drug in [normalize_drug(d) for d in cfg["antibiotics"]]:
        train_drug(features, labels, splits, drug, cfg)


if __name__ == "__main__":
    main()
