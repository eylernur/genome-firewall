"""Module 02: homology-based clustering -> grouped train/calib/test split.

WHY: the #1 thing separating a strong submission from an inflated one. Near-identical
genomes must NEVER appear in both train and test. We cluster genomes by sequence
similarity and split by CLUSTER, not by row.

Default method = Mash (fast whole-genome k-mer sketch distance).
  conda install -c bioconda mash
  mash sketch -o sketch data/raw/*.fna
  mash dist sketch.msh sketch.msh > dist.tab   # pairwise distances
Clusters = connected components where (1 - mash_distance) >= homology_threshold.

Outputs: data/processed/splits.json
  { "clusters": {genome_id: cluster_id},
    "train": [...ids], "calib": [...ids], "test": [...ids],
    "cv_folds": [[train_idx,test_idx],...] }
"""
from __future__ import annotations
import argparse
import json
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd

from utils import load_config, resolve, get_logger

log = get_logger("split")


def mash_clusters(fna_dir: Path, work: Path, threshold: float) -> dict[str, int]:
    """Return {genome_id: cluster_id} via Mash + union-find at (1-dist) >= threshold."""
    fnas = sorted(fna_dir.glob("*.fna"))
    ids = [f.stem for f in fnas]
    if len(fnas) < 2:
        return {i: idx for idx, i in enumerate(ids)}

    sketch = work / "sketch"
    dist = work / "dist.tab"
    try:
        subprocess.run(["mash", "sketch", "-o", str(sketch), *[str(f) for f in fnas]],
                       check=True, capture_output=True, text=True)
        with open(dist, "w") as fh:
            subprocess.run(["mash", "dist", f"{sketch}.msh", f"{sketch}.msh"],
                           check=True, stdout=fh, text=True)
    except (FileNotFoundError, subprocess.CalledProcessError) as e:
        log.warning("Mash unavailable/failed (%s). Falling back to per-genome clusters.", e)
        return {i: idx for idx, i in enumerate(ids)}

    # union-find
    parent = {i: i for i in ids}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    stem = {Path(f).stem: Path(f).stem for f in fnas}
    with open(dist) as fh:
        for line in fh:
            ref, qry, d, *_ = line.split("\t")
            gi, gj = Path(ref).stem, Path(qry).stem
            if gi == gj:
                continue
            similarity = 1.0 - float(d)
            if similarity >= threshold:
                union(stem.get(gi, gi), stem.get(gj, gj))

    roots = {}
    clusters = {}
    for i in ids:
        r = find(i)
        if r not in roots:
            roots[r] = len(roots)
        clusters[i] = roots[r]
    log.info("Mash clustering: %d genomes -> %d clusters", len(ids), len(roots))
    return clusters


def grouped_split(labels: pd.DataFrame, clusters: dict[str, int], cfg: dict):
    import numpy as np
    from sklearn.model_selection import StratifiedGroupKFold

    rng = cfg["project"]["seed"]
    labels = labels.copy()
    labels["cluster"] = labels["genome_id"].map(clusters)
    labels = labels[labels["cluster"].notna()]

    # collapse to genome level for splitting (a genome has multiple drug rows)
    g = labels.groupby("genome_id").agg(cluster=("cluster", "first"),
                                        y=("label", "max")).reset_index()

    # ---- Greedy cluster -> split assignment ----
    # GroupShuffleSplit fails badly when one clonal cluster dominates (it can dump
    # thousands of genomes into test). Instead, sort clusters largest-first and
    # deal them out to test/calib/train until each hits its genome-count target.
    # This keeps clusters intact (no homology leakage) AND respects the ratio.
    test_frac = cfg["split"]["test_frac"]
    calib_frac = cfg["split"]["calib_frac"]
    n_total = len(g)
    target_test = int(round(n_total * test_frac))
    target_calib = int(round(n_total * calib_frac))

    from sklearn.model_selection import train_test_split

    # Step 1: TEST = the smallest clusters (distinct genetic groups) until we hit the
    # target. These are held out cleanly by cluster -> honest generalization, no leakage.
    sizes = g.groupby("cluster").size().sort_values(ascending=True)  # smallest first
    assign = {}
    n_test = 0
    for cid in sizes.index:
        sz = int(sizes[cid])
        if n_test + sz <= max(target_test, 1) and n_test < target_test:
            assign[cid] = "test"; n_test += sz
        else:
            assign[cid] = "train"
    g["split"] = g["cluster"].map(assign)

    # Step 2: CALIB is carved out of the TRAIN pool (stratified). With one dominant
    # clonal cluster there's no separate group to spare for calibration, so we take a
    # random stratified slice of train. This is fine: calibration only needs a
    # representative probability distribution; generalization is still judged on the
    # cluster-clean TEST set above.
    train_mask = g["split"] == "train"
    train_pool = g[train_mask]
    if len(train_pool) > 50 and train_pool["y"].nunique() > 1:
        cal_frac = calib_frac / (1 - test_frac)
        tr, ca = train_test_split(train_pool, test_size=cal_frac,
                                  stratify=train_pool["y"], random_state=rng)
        g.loc[ca.index, "split"] = "calib"

    # safety net: never allow an empty train or test
    if (g["split"] == "train").sum() == 0 or (g["split"] == "test").sum() == 0:
        log.warning("Degenerate split — falling back to a stratified row split.")
        tr, tmp = train_test_split(g, test_size=test_frac + calib_frac,
                                   stratify=g["y"], random_state=rng)
        ca, te = train_test_split(tmp, test_size=test_frac / (test_frac + calib_frac),
                                  stratify=tmp["y"], random_state=rng)
        g["split"] = "train"
        g.loc[ca.index, "split"] = "calib"
        g.loc[te.index, "split"] = "test"

    train = g[g["split"] == "train"]
    calib = g[g["split"] == "calib"]
    test = g[g["split"] == "test"]
    log.info("Greedy split by cluster -> train=%d calib=%d test=%d genomes",
             len(train), len(calib), len(test))

    # 3) CV folds on train for model selection (grouped + stratified).
    #    Best-effort only (not consumed downstream): skip cleanly when the train set
    #    is too small / has too few clusters (e.g. the 20-genome smoke test).
    folds = []
    tr_ids = train["genome_id"].tolist()
    n_clusters = train["cluster"].nunique()
    n_folds = min(cfg["split"]["n_folds"], n_clusters)
    if n_folds >= 2 and train["y"].nunique() > 1 and len(train) >= n_folds:
        try:
            sgkf = StratifiedGroupKFold(n_splits=n_folds, shuffle=True, random_state=rng)
            for tr_i, te_i in sgkf.split(train, train["y"], groups=train["cluster"]):
                folds.append(([tr_ids[i] for i in tr_i], [tr_ids[i] for i in te_i]))
        except ValueError as e:
            log.warning("Skipping CV folds (small/degenerate data): %s", e)
    else:
        log.warning("Skipping CV folds: only %d train clusters / %d genomes.",
                    n_clusters, len(train))

    return {
        "clusters": {k: int(v) for k, v in clusters.items()},
        "train": train["genome_id"].tolist(),
        "calib": calib["genome_id"].tolist(),
        "test": test["genome_id"].tolist(),
        "cv_folds": folds,
        "homology_threshold": cfg["split"]["homology_threshold"],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=None)
    args = ap.parse_args()
    cfg = load_config(args.config)

    proc = resolve(cfg["paths"]["processed_dir"])
    labels = pd.read_parquet(proc / "labels.parquet")
    fna_dir = resolve(cfg["paths"]["raw_dir"])
    work = resolve(cfg["paths"]["interim_dir"])

    # Only split over genomes we actually annotated (present in the feature matrix).
    feat_path = resolve(cfg["features"]["matrix_path"])
    if feat_path.exists():
        feat_ids = set(pd.read_parquet(feat_path).index.astype(str))
        before = labels["genome_id"].nunique()
        labels = labels[labels["genome_id"].astype(str).isin(feat_ids)]
        log.info("Restricting split to annotated genomes: %d -> %d",
                 before, labels["genome_id"].nunique())

    clusters = mash_clusters(fna_dir, work, cfg["split"]["homology_threshold"])
    splits = grouped_split(labels, clusters, cfg)

    out = resolve(cfg["split"]["splits_path"])
    out.write_text(json.dumps(splits, indent=2))
    log.info("splits.json: train=%d calib=%d test=%d",
             len(splits["train"]), len(splits["calib"]), len(splits["test"]))


if __name__ == "__main__":
    main()
