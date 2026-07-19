"""Module 03: honest evidence categorization + optional plain-language prose.

Evidence categories (from the brief):
  (i)   known resistance gene / DNA change detected
  (ii)  statistical association only (top model weight, NOT a curated mechanism)
  (iii) no known resistance signal found

CRITICAL honesty rule: a high model coefficient / SHAP value is a STATISTICAL
association, never a proof of biological cause. We label it as such and never let the
optional LLM invent a mechanism — it only rephrases the structured facts we pass it.
"""
from __future__ import annotations
import os

import numpy as np
import pandas as pd

from utils import load_config, get_logger

log = get_logger("explain")


def evidence_for(prediction_call: str, active_features: list[str], drug_class_map: dict,
                 model_top_features: list[str], drug: str) -> dict:
    """Return {evidence_type, detected_genes, statistical_features, note}."""
    # features known to AMRFinderPlus == curated resistance determinants (category i)
    known_hits = [f for f in active_features if f in drug_class_map]

    if prediction_call == "likely to fail" and known_hits:
        return {
            "evidence_type": "known_resistance_mechanism",
            "detected_genes": known_hits,
            "statistical_features": [],
            "note": "A curated resistance gene / mutation was detected for this drug class.",
        }
    # statistical-only: model leaned on features that aren't curated mechanisms
    stat = [f for f in model_top_features if f in set(active_features) and f not in drug_class_map]
    if stat:
        return {
            "evidence_type": "statistical_association_only",
            "detected_genes": [],
            "statistical_features": stat[:5],
            "note": ("Prediction driven by a statistical association, NOT a proven biological "
                     "cause. Feature-importance is not mechanistic evidence."),
        }
    return {
        "evidence_type": "no_known_signal",
        "detected_genes": [],
        "statistical_features": [],
        "note": "No known resistance signal was found for this drug.",
    }


def top_features_for_drug(bundle, k: int = 15) -> list[str]:
    clf = bundle["pipeline"]
    coefs = np.ravel(clf.coef_)
    order = np.argsort(-np.abs(coefs))[:k]
    feats = bundle["features"]
    return [feats[i] for i in order]


def drug_class_features(dictionary: pd.DataFrame, drug_class_keywords: list[str]) -> set[str]:
    """Which curated features belong to this drug's class (for category i)."""
    if dictionary.empty:
        return set()
    mask = dictionary["drug_class"].fillna("").str.lower().apply(
        lambda c: any(k in c for k in drug_class_keywords))
    return set(dictionary[mask]["feature"])


def maybe_llm_prose(structured: dict, cfg: dict) -> str | None:
    """Optional: turn structured facts into one plain sentence. Facts only — no invention."""
    if not cfg["llm"]["enabled"] or not os.getenv("OPENAI_API_KEY"):
        return None
    try:
        from openai import OpenAI
        client = OpenAI()
        prompt = (
            "You are a careful clinical decision-support assistant. Write ONE short, neutral "
            "sentence summarizing ONLY these facts. Do not invent mechanisms or add certainty. "
            f"Facts: {structured}"
        )
        r = client.chat.completions.create(
            model=cfg["llm"]["model"],
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=80,
        )
        return r.choices[0].message.content.strip()
    except Exception as e:  # noqa: BLE001
        log.warning("LLM prose skipped: %s", e)
        return None
