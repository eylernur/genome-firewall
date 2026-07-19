"""Module 01 (data): download genomes + LAB-MEASURED AMR phenotypes from BV-BRC.

Uses the BV-BRC **Data API over HTTPS** (https://www.bv-brc.org/api/) — this works
through institutional/hackathon firewalls, unlike the FTP/FTPS bulk site (which BV-BRC
now serves only over encrypted FTPS and which many networks block).

Outputs:
  data/processed/labels.parquet   -> one label per (genome_id, antibiotic)
  data/raw/<genome_id>.fna         -> assembled contigs per genome
  data/raw/manifest.csv            -> source/accession/license audit trail

CRITICAL: we keep only rows where evidence == "Laboratory Method" (exact field in the
API) and drop "Computational Method" rows, exactly as the challenge requires.

API refs:
  genome_amr:      https://www.bv-brc.org/api/genome_amr/
  genome_sequence: https://www.bv-brc.org/api/genome_sequence/  (FASTA via http_accept=application/dna+fasta)
"""
from __future__ import annotations
import argparse
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from tqdm import tqdm

from utils import load_config, resolve, get_logger, normalize_drug, safe_id, ensure_dirs

log = get_logger("ingest")

API = "https://www.bv-brc.org/api"
CONTENT_TYPE = "application/rqlquery+x-www-form-urlencoded"
PAGE = 25000          # BV-BRC max rows per request
TIMEOUT = 120


def _make_session() -> requests.Session:
    """A requests session with automatic retries + backoff (survives flaky wifi)."""
    s = requests.Session()
    retry = Retry(total=5, connect=5, read=5, backoff_factor=1.5,
                  status_forcelist=[429, 500, 502, 503, 504],
                  allowed_methods=["GET", "POST"])
    adapter = HTTPAdapter(max_retries=retry, pool_connections=16, pool_maxsize=16)
    s.mount("https://", adapter)
    return s


SESSION = _make_session()


def _post(core: str, rql: str, accept: str = "application/json"):
    """POST an RQL query to a BV-BRC data core (POST avoids URL-length limits)."""
    url = f"{API}/{core}/"
    r = SESSION.post(url, data=rql,
                     headers={"Content-Type": CONTENT_TYPE, "Accept": accept},
                     timeout=TIMEOUT)
    r.raise_for_status()
    return r


def fetch_amr(cfg: dict) -> pd.DataFrame:
    """Page through all LAB-measured AMR rows for the species' taxon."""
    taxon = cfg["species"]["bvbrc_taxon_id"]
    rows, offset = [], 0
    while True:
        rql = (f"and(eq(taxon_id,{taxon}),eq(evidence,%22Laboratory%20Method%22))"
               f"&sort(%2Bid)&limit({PAGE},{offset})")
        data = _post("genome_amr", rql).json()
        if not data:
            break
        rows.extend(data)
        log.info("fetched %d AMR rows (offset %d)", len(rows), offset)
        if len(data) < PAGE:
            break
        offset += PAGE
        time.sleep(0.5)
    df = pd.DataFrame(rows)
    log.info("Total lab-measured AMR rows for taxon %s: %d", taxon, len(df))
    return df


def build_labels(df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    lab = cfg["labels"]
    wanted = {normalize_drug(a) for a in cfg["antibiotics"]}
    if df.empty:
        raise SystemExit("No AMR rows returned — check taxon_id / network.")

    df = df.copy()
    df["antibiotic_norm"] = df["antibiotic"].apply(normalize_drug)
    df = df[df["antibiotic_norm"].isin(wanted)]
    log.info("After antibiotic filter: %d rows", len(df))

    pheno = df["resistant_phenotype"].fillna("").str.strip().str.capitalize()
    df = df[~pheno.isin([v.capitalize() for v in lab["drop_values"]])]
    label = pheno.map({
        lab["resistant_value"].capitalize(): 1,     # resistant -> "likely to fail"
        lab["susceptible_value"].capitalize(): 0,   # susceptible -> "likely to work"
    })
    df = df.assign(label=label)
    df = df[df["label"].notna()]
    df["label"] = df["label"].astype(int)

    # collapse to one label per (genome, antibiotic): majority vote, drop ties
    agg = df.groupby(["genome_id", "antibiotic_norm"])["label"].mean().reset_index()
    agg = agg[agg["label"] != 0.5]
    agg["label"] = (agg["label"] >= 0.5).astype(int)
    log.info("Final (genome, antibiotic) label pairs: %d across %d genomes",
             len(agg), agg["genome_id"].nunique())
    return agg.rename(columns={"antibiotic_norm": "antibiotic"})


def fetch_fasta(genome_id: str) -> bytes | None:
    """Get all contigs for a genome as FASTA via the HTTPS Data API."""
    rql = f"eq(genome_id,{genome_id})&limit(25000)"
    try:
        r = _post("genome_sequence", rql, accept="application/dna+fasta")
        if r.content and r.content.startswith(b">"):
            return r.content
    except Exception as e:  # noqa: BLE001
        log.warning("API FASTA failed for %s: %s", genome_id, e)
    return None


def _one_genome(gid: str, raw_dir: Path) -> dict:
    fna = raw_dir / f"{safe_id(gid)}.fna"
    if fna.exists() and fna.stat().st_size > 0:
        status = "cached"
    else:
        content = fetch_fasta(gid)
        if content:
            fna.write_bytes(content)
            status = "downloaded"
        else:
            status = "FAILED"
    return {"genome_id": gid, "fna_path": str(fna), "source": "BV-BRC Data API",
            "url": f"{API}/genome_sequence/?eq(genome_id,{gid})",
            "license": "BV-BRC public data", "status": status}


def download_genomes(genome_ids, raw_dir: Path, workers: int = 6) -> pd.DataFrame:
    """Parallel + resumable: already-downloaded genomes are skipped, so re-running
    ingest just fills the gaps until every genome is present."""
    ids = sorted(set(genome_ids))
    rows = []
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(_one_genome, gid, raw_dir): gid for gid in ids}
        for fut in tqdm(as_completed(futs), total=len(futs), desc="genomes"):
            rows.append(fut.result())
    df = pd.DataFrame(rows)
    n_fail = int((df["status"] == "FAILED").sum())
    if n_fail:
        log.warning("%d genomes still failed — just re-run ingest to retry only those.", n_fail)
    return df


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=None)
    ap.add_argument("--max-genomes", type=int, default=None, help="cap for a quick smoke test")
    ap.add_argument("--workers", type=int, default=6, help="parallel genome downloads")
    ap.add_argument("--skip-fna", action="store_true", help="labels only, skip genome download")
    args = ap.parse_args()

    cfg = load_config(args.config)
    ensure_dirs(cfg)
    raw_dir = resolve(cfg["paths"]["raw_dir"])
    proc_dir = resolve(cfg["paths"]["processed_dir"])

    amr = fetch_amr(cfg)
    labels = build_labels(amr, cfg)

    if args.max_genomes:
        keep = labels["genome_id"].drop_duplicates().head(args.max_genomes)
        labels = labels[labels["genome_id"].isin(keep)]
        log.info("Capped to %d genomes for smoke test", len(keep))

    labels.to_parquet(proc_dir / "labels.parquet", index=False)
    log.info("Wrote %s (%d rows)", proc_dir / "labels.parquet", len(labels))

    if not args.skip_fna:
        manifest = download_genomes(labels["genome_id"].unique(), raw_dir, workers=args.workers)
        manifest.to_csv(raw_dir / "manifest.csv", index=False)
        n_ok = (manifest["status"].isin(["downloaded", "cached"])).sum()
        log.info("Genomes ready: %d / %d (see data/raw/manifest.csv)", n_ok, len(manifest))


if __name__ == "__main__":
    main()
