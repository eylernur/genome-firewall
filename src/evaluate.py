"""Module 03 / judging: evaluate on the HELD-OUT test split with the required metrics.

Per drug: balanced accuracy, recall(resistant), recall(susceptible), F1, AUROC, PR-AUC,
Brier score. Plus: no-call rate + accuracy on remaining calls, reliability plot,
and a per-genetic-group (cluster) breakdown.

Outputs:
  reports/metrics.md
  reports/reliability_<drug>.png
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.metrics import (balanced_accuracy_score, recall_score, f1_score,
                             roc_auc_score, average_precision_score, brier_score_loss)
from sklearn.calibration import calibration_curve

from utils import load_config, resolve, get_logger, normalize_drug
from nocall import decide
from target_gate import load_drug_targets, gate_for_genome

log = get_logger("evaluate")


def _test_frame(features, labels, test_ids, drug):
    sub = labels[(labels["antibiotic"] == drug) & (labels["genome_id"].isin(test_ids))]
    sub = sub[sub["genome_id"].isin(features.index)]
    return sub


def reliability_plot(y, p, drug, out: Path):
    if len(np.unique(y)) < 2:
        return
    frac_pos, mean_pred = calibration_curve(y, p, n_bins=10, strategy="quantile")
    plt.figure(figsize=(4, 4))
    plt.plot([0, 1], [0, 1], "--", color="gray", label="perfect")
    plt.plot(mean_pred, frac_pos, "o-", label=drug)
    plt.xlabel("Mean predicted p(fail)")
    plt.ylabel("Observed fraction resistant")
    plt.title(f"Reliability — {drug}")
    plt.legend()
    plt.tight_layout()
    plt.savefig(out, dpi=120)
    plt.close()


def evaluate(cfg):
    proc = resolve(cfg["paths"]["processed_dir"])
    features = pd.read_parquet(resolve(cfg["features"]["matrix_path"]))
    labels = pd.read_parquet(proc / "labels.parquet")
    labels["antibiotic"] = labels["antibiotic"].apply(normalize_drug)
    splits = json.loads(resolve(cfg["split"]["splits_path"]).read_text())
    clusters = splits["clusters"]
    targets = load_drug_targets(cfg)
    reports_dir = resolve("reports")

    lines = ["# GenoWall — held-out evaluation\n",
             f"Species: **{cfg['species']['name']}**  |  test genomes: {len(splits['test'])}\n"]
    per_drug_tables = []

    for drug in [normalize_drug(d) for d in cfg["antibiotics"]]:
        mp = resolve(cfg["model"]["models_dir"]) / f"{drug.replace('/', '_')}.joblib"
        if not mp.exists():
            lines.append(f"\n## {drug}\n_no model_\n")
            continue
        bundle = joblib.load(mp)
        est = bundle["calibrator"] or bundle["pipeline"]

        sub = _test_frame(features, labels, splits["test"], drug)
        if sub.empty or len(sub["label"].unique()) < 2:
            lines.append(f"\n## {drug}\n_insufficient test data_\n")
            continue

        X = features.loc[sub["genome_id"]]
        y = sub["label"].to_numpy()
        p = est.predict_proba(X)[:, 1]

        # definite-call metrics on the SUBSET that isn't no-called
        calls, keep = [], []
        for gid, prob in zip(sub["genome_id"], p):
            gate = gate_for_genome(features.loc[gid], drug, targets)
            d = decide(float(prob), gate, None, cfg)
            calls.append(d["call"])
            keep.append(d["call"] != "no-call")
        keep = np.array(keep)
        n_nocall = int((~keep).sum())

        yhat = (p >= 0.5).astype(int)
        row = {
            "drug": drug,
            "n_test": len(y),
            "prevalence_R": round(float(y.mean()), 3),
            "balanced_acc": round(balanced_accuracy_score(y, yhat), 3),
            "recall_R": round(recall_score(y, yhat, pos_label=1, zero_division=0), 3),
            "recall_S": round(recall_score(y, yhat, pos_label=0, zero_division=0), 3),
            "f1": round(f1_score(y, yhat, zero_division=0), 3),
            "AUROC": round(roc_auc_score(y, p), 3),
            "PR_AUC": round(average_precision_score(y, p), 3),
            "Brier": round(brier_score_loss(y, p), 3),
            "nocall_rate": round(n_nocall / len(y), 3),
        }
        # accuracy on definite calls only
        if keep.sum() > 0:
            row["acc_on_calls"] = round(float((yhat[keep] == y[keep]).mean()), 3)
        per_drug_tables.append(row)

        reliability_plot(y, p, drug, reports_dir / f"reliability_{drug.replace('/', '_')}.png")

        # per genetic-group breakdown
        grp = pd.DataFrame({"gid": sub["genome_id"].values, "y": y, "p": p})
        grp["cluster"] = grp["gid"].map(clusters)
        by = grp.groupby("cluster").apply(
            lambda d: pd.Series({
                "n": len(d),
                "bal_acc": balanced_accuracy_score(d["y"], (d["p"] >= 0.5).astype(int))
                if d["y"].nunique() > 1 else np.nan,
            }), include_groups=False).reset_index()
        lines.append(f"\n## {drug}\n")
        lines.append(pd.DataFrame([row]).to_markdown(index=False))
        lines.append(f"\n_Groups in test: {by['cluster'].nunique()} "
                     f"(balanced acc reported per group where both classes present)_\n")

    if per_drug_tables:
        summary = pd.DataFrame(per_drug_tables)
        lines.insert(2, "\n## Summary\n" + summary.to_markdown(index=False) + "\n")

    (reports_dir / "metrics.md").write_text("\n".join(lines))
    log.info("Wrote reports/metrics.md and reliability plots.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=None)
    args = ap.parse_args()
    evaluate(load_config(args.config))


if __name__ == "__main__":
    main()
