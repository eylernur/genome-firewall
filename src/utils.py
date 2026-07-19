"""Shared helpers: config loading, paths, logging, name normalization."""
from __future__ import annotations
import logging
import os
import re
from pathlib import Path
from functools import lru_cache

import yaml

ROOT = Path(__file__).resolve().parent.parent


def get_logger(name: str) -> logging.Logger:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%H:%M:%S",
    )
    return logging.getLogger(name)


@lru_cache(maxsize=1)
def load_config(path: str | None = None) -> dict:
    cfg_path = Path(path) if path else ROOT / "config.yaml"
    with open(cfg_path) as fh:
        cfg = yaml.safe_load(fh)
    return cfg


def resolve(rel: str) -> Path:
    """Resolve a config-relative path against the repo root."""
    p = Path(rel)
    return p if p.is_absolute() else ROOT / p


def normalize_drug(name: str) -> str:
    """Standardize an antibiotic name for joining across sources."""
    if name is None:
        return ""
    n = name.strip().lower()
    n = n.replace("_", "/").replace(" ", "")
    aliases = {
        "trimethoprim/sulfamethoxazole": "trimethoprim/sulfamethoxazole",
        "co-trimoxazole": "trimethoprim/sulfamethoxazole",
        "sxt": "trimethoprim/sulfamethoxazole",
        "cip": "ciprofloxacin",
        "gen": "gentamicin",
        "mem": "meropenem",
        "caz": "ceftazidime",
    }
    return aliases.get(n, n)


def ensure_dirs(cfg: dict) -> None:
    for key in ("raw_dir", "interim_dir", "processed_dir"):
        resolve(cfg["paths"][key]).mkdir(parents=True, exist_ok=True)
    resolve(cfg["model"]["models_dir"]).mkdir(parents=True, exist_ok=True)
    resolve("reports").mkdir(parents=True, exist_ok=True)


def safe_id(genome_id: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]", "_", str(genome_id))
