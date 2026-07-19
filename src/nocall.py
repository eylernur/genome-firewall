"""Module 03: no-call logic. Returns a call from a calibrated probability + context.

no-call when ANY of:
  (a) calibrated prob in the uncertain band [uncertain_low, uncertain_high]
  (b) drug-target gate conflicts with the model (gate says target_absent)
  (c) genome is out-of-distribution: max similarity to any TRAIN cluster < ood_min_similarity

Returns dict: {call, prob_fail, confidence, reason}
  call in {"likely to fail", "likely to work", "no-call"}
  confidence = distance of prob from 0.5, scaled to [0,1] (only meaningful for a definite call)
"""
from __future__ import annotations
from utils import load_config


def decide(prob_fail: float, gate: str, ood_similarity: float | None, cfg: dict) -> dict:
    nc = cfg["nocall"]
    reasons = []

    ood = ood_similarity is not None and ood_similarity < nc["ood_min_similarity"]
    if ood:
        reasons.append(f"genome unlike training data (max similarity {ood_similarity:.2f} "
                       f"< {nc['ood_min_similarity']})")

    if nc["gate_conflict_is_nocall"] and gate == "target_absent":
        reasons.append("drug target appears absent/disrupted (gate conflict)")

    uncertain = nc["uncertain_low"] <= prob_fail <= nc["uncertain_high"]
    if uncertain:
        reasons.append(f"confidence too low (p_fail={prob_fail:.2f} in the uncertain band)")

    if reasons:
        return {"call": "no-call", "prob_fail": prob_fail, "confidence": None,
                "reason": "; ".join(reasons)}

    call = "likely to fail" if prob_fail >= 0.5 else "likely to work"
    confidence = abs(prob_fail - 0.5) * 2.0   # 0..1
    return {"call": call, "prob_fail": prob_fail, "confidence": round(confidence, 3), "reason": ""}


if __name__ == "__main__":
    cfg = load_config()
    for p in (0.05, 0.45, 0.55, 0.95):
        print(p, decide(p, "target_present", 0.99, cfg))
    print("OOD:", decide(0.9, "target_present", 0.5, cfg))
    print("gate:", decide(0.9, "target_absent", 0.99, cfg))
