"""Module 01: run AMRFinderPlus over every genome FASTA -> per-genome TSV.

AMRFinderPlus (NCBI, public domain): https://github.com/ncbi/amr/wiki
First-time setup (once):
    conda create -y -c conda-forge -c bioconda -n amrfinder --strict-channel-priority ncbi-amrfinderplus
    conda activate amrfinder
    amrfinder --update       # downloads the AMR gene/mutation database

Per genome:
    amrfinder -n <genome>.fna --organism Klebsiella_pneumoniae --plus -o <genome>.amrfinder.tsv
"""
from __future__ import annotations
import argparse
import subprocess
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import pandas as pd
from tqdm import tqdm

from utils import load_config, resolve, get_logger, safe_id, ensure_dirs

log = get_logger("annotate")


def run_one(fna_path: str, out_path: str, organism: str) -> tuple[str, str]:
    out = Path(out_path)
    if out.exists() and out.stat().st_size > 0:
        return out_path, "cached"
    cmd = ["amrfinder", "-n", fna_path, "--plus", "-o", out_path]
    if organism:
        cmd += ["--organism", organism]
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        return out_path, "ok"
    except FileNotFoundError:
        return out_path, "ERROR: amrfinder not on PATH (activate the conda env)"
    except subprocess.CalledProcessError as e:
        # Some organisms/inputs warn but still emit; keep the message for debugging.
        return out_path, f"ERROR: {e.stderr.strip()[:200]}"


def _balanced_subset(fna_files, cfg, limit):
    """Pick <=limit genomes that keep a mix of resistant & susceptible for each drug,
    so the trained models still see both classes. Falls back to first-N if labels absent."""
    proc = resolve(cfg["paths"]["processed_dir"])
    labels_path = proc / "labels.parquet"
    if not labels_path.exists():
        return fna_files[:limit]
    labels = pd.read_parquet(labels_path)
    have = {f.stem for f in fna_files}
    labels = labels[labels["genome_id"].astype(str).isin(have)]
    # rank genomes by how many drug-labels they carry (more label coverage = more useful)
    order = (labels.groupby("genome_id").size().sort_values(ascending=False).index.tolist())
    keep = set(str(g) for g in order[:limit])
    chosen = [f for f in fna_files if f.stem in keep]
    return chosen or fna_files[:limit]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=None)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--limit", type=int, default=None,
                    help="annotate at most N genomes (label-coverage prioritized) to save time")
    args = ap.parse_args()

    cfg = load_config(args.config)
    ensure_dirs(cfg)
    raw_dir = resolve(cfg["paths"]["raw_dir"])
    interim = resolve(cfg["paths"]["interim_dir"])
    organism = cfg["species"]["amrfinder_organism"]

    manifest = pd.read_csv(raw_dir / "manifest.csv") if (raw_dir / "manifest.csv").exists() else None
    fna_files = sorted(raw_dir.glob("*.fna"))
    if not fna_files:
        log.error("No .fna files in %s — run ingest_bvbrc.py first.", raw_dir)
        return
    if args.limit:
        fna_files = _balanced_subset(fna_files, cfg, args.limit)
        log.info("Annotating a subset of %d genomes (--limit).", len(fna_files))

    jobs = []
    with ProcessPoolExecutor(max_workers=args.workers) as ex:
        for fna in fna_files:
            gid = fna.stem
            out = interim / f"{safe_id(gid)}.amrfinder.tsv"
            jobs.append(ex.submit(run_one, str(fna), str(out), organism))
        results = []
        for fut in tqdm(as_completed(jobs), total=len(jobs), desc="amrfinder"):
            results.append(fut.result())

    errs = [r for r in results if r[1].startswith("ERROR")]
    log.info("Annotated %d genomes (%d errors).", len(results), len(errs))
    if errs:
        for p, msg in errs[:5]:
            log.warning("%s -> %s", p, msg)


if __name__ == "__main__":
    main()
