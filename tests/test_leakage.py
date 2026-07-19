"""Guard rails: the anti-leakage invariant + config sanity + no-call logic.

Run:  pytest -q   (or: python -m pytest tests/ -q)
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from utils import load_config, normalize_drug  # noqa: E402
from nocall import decide  # noqa: E402


def test_config_loads():
    cfg = load_config()
    assert cfg["species"]["name"]
    assert 1 <= len(cfg["antibiotics"]) <= 6
    assert 0 < cfg["split"]["test_frac"] < 1


def test_drug_normalization():
    assert normalize_drug("Ciprofloxacin") == "ciprofloxacin"
    assert normalize_drug("co-trimoxazole") == "trimethoprim/sulfamethoxazole"
    assert normalize_drug("CAZ") == "ceftazidime"


def test_nocall_bands():
    cfg = load_config()
    # confident fail / work
    assert decide(0.95, "target_present", 0.99, cfg)["call"] == "likely to fail"
    assert decide(0.02, "target_present", 0.99, cfg)["call"] == "likely to work"
    # uncertain band -> no-call
    assert decide(0.50, "target_present", 0.99, cfg)["call"] == "no-call"
    # gate conflict -> no-call
    assert decide(0.95, "target_absent", 0.99, cfg)["call"] == "no-call"
    # OOD -> no-call
    assert decide(0.95, "target_present", 0.10, cfg)["call"] == "no-call"


@pytest.mark.skipif(not (ROOT / "data/processed/splits.json").exists(),
                    reason="run cluster_split.py first")
def test_no_cluster_leakage():
    splits = json.loads((ROOT / "data/processed/splits.json").read_text())
    clusters = splits["clusters"]

    def cluster_set(ids):
        return {clusters[i] for i in ids if i in clusters}

    tr, ca, te = map(cluster_set, (splits["train"], splits["calib"], splits["test"]))
    assert tr.isdisjoint(te), "TRAIN and TEST share a homology cluster — leakage!"
    assert ca.isdisjoint(te), "CALIB and TEST share a homology cluster — leakage!"
    assert tr.isdisjoint(ca), "TRAIN and CALIB share a homology cluster — leakage!"
