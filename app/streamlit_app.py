"""Module 03: GenoWall — Decision Report app (polished UI).

Run:  streamlit run app/streamlit_app.py
Upload a genome FASTA -> per-antibiotic report with calibrated confidence, evidence
category, no-call handling, and a mandatory 'confirm with lab testing' banner.
"""
from __future__ import annotations
import sys
import tempfile
from pathlib import Path

import streamlit as st
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from utils import load_config  # noqa: E402
from predict import predict_report  # noqa: E402

st.set_page_config(page_title="GenoWall", page_icon="🧬", layout="wide")
cfg = load_config()

# ------------------------------------------------------------------ styling
st.markdown("""
<style>
:root{
  --fail:#e5484d; --work:#30a46c; --nocall:#8b8d98;
  --bg-card:#111827; --border:#1f2937; --muted:#9ca3af;
}
.block-container{padding-top:2rem;max-width:1200px;}
#MainMenu, footer{visibility:hidden;}

.gf-hero{
  background:linear-gradient(120deg,#0b1220 0%,#12203a 55%,#0e2a2a 100%);
  border:1px solid #1e2a44;border-radius:18px;padding:26px 30px;margin-bottom:14px;
}
.gf-hero h1{margin:0;font-size:2.2rem;font-weight:800;letter-spacing:-.5px;
  background:linear-gradient(90deg,#7dd3fc,#a78bfa);-webkit-background-clip:text;
  -webkit-text-fill-color:transparent;}
.gf-hero p{margin:.4rem 0 0;color:#c7d2e0;font-size:1rem;}

.gf-banner{background:#2a1618;border:1px solid #7f2a2f;color:#ffb4b7;
  border-radius:12px;padding:12px 16px;font-weight:600;margin:10px 0;}
.gf-safe{background:#0f2027;border:1px solid #1f4a4a;color:#a7e8d8;
  border-radius:12px;padding:10px 16px;margin:6px 0 18px;font-size:.92rem;}

.gf-meta{display:flex;gap:34px;margin:6px 0 4px;}
.gf-meta .lbl{color:var(--muted);font-size:.72rem;text-transform:uppercase;letter-spacing:.6px;}
.gf-meta .val{font-size:1.35rem;font-weight:700;color:#e8eef7;}

.gf-card{background:var(--bg-card);border:1px solid var(--border);border-radius:16px;
  padding:18px 18px 14px;height:100%;}
.gf-card.fail{border-top:4px solid var(--fail);}
.gf-card.work{border-top:4px solid var(--work);}
.gf-card.nocall{border-top:4px solid var(--nocall);}
.gf-drug{font-size:1.15rem;font-weight:700;color:#e8eef7;margin:0 0 2px;text-transform:capitalize;}
.gf-verdict{font-weight:800;font-size:1.05rem;margin:2px 0 10px;}
.gf-verdict.fail{color:var(--fail);}
.gf-verdict.work{color:var(--work);}
.gf-verdict.nocall{color:var(--nocall);}
.gf-conf-track{background:#1f2937;border-radius:99px;height:8px;overflow:hidden;margin:2px 0 4px;}
.gf-conf-fill{height:8px;border-radius:99px;}
.gf-small{color:var(--muted);font-size:.78rem;margin:2px 0;}
.gf-gene{background:#0f2a1e;border:1px solid #1f5a3d;color:#7ee2b0;border-radius:9px;
  padding:7px 10px;font-size:.82rem;margin-top:8px;font-family:ui-monospace,monospace;}
.gf-none{background:#12233b;border:1px solid #244a73;color:#9dc3ef;border-radius:9px;
  padding:7px 10px;font-size:.82rem;margin-top:8px;}
.gf-stat{background:#2a2410;border:1px solid #6b5a1f;color:#e6d18a;border-radius:9px;
  padding:7px 10px;font-size:.82rem;margin-top:8px;}
</style>
""", unsafe_allow_html=True)

# ------------------------------------------------------------------ header
st.markdown(f"""
<div class="gf-hero">
  <h1>🧬 GenoWall</h1>
  <p>An AI defense system against superbugs — predict which antibiotics may fail
     from a bacterial genome, <b>before</b> standard lab results arrive.</p>
</div>
<div class="gf-banner">⚠️ {cfg['report']['lab_banner']}</div>
<div class="gf-safe">🛡️ {cfg['report']['defensive_note']}</div>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("### 🔬 Scope")
    st.markdown(f"**Species**  \n{cfg['species']['name']}")
    st.markdown("**Antibiotics**  \n" + "  \n".join(f"• {a}" for a in cfg["antibiotics"]))
    st.divider()
    st.markdown("**Held-out performance**")
    st.caption("AUROC 0.94–0.98 · balanced acc ~0.93 · Brier ~0.045 · "
               "grouped by genetic similarity")
    st.divider()
    st.caption("Out of scope: sample collection, species ID, genome assembly, "
               "organism design. Decision support only — confirm with lab testing.")

# drug -> molecular target genes (for the target-gate display)
try:
    _dr = pd.read_csv(Path(__file__).resolve().parent.parent / "drugs.csv")
    DRUG_TARGETS = {r["antibiotic"].strip().lower():
                    [t.strip() for t in str(r["molecular_target_genes"]).split(";") if t.strip()]
                    for _, r in _dr.iterrows()}
except Exception:
    DRUG_TARGETS = {}

STYLE = {"likely to fail": ("fail", "#e5484d", "LIKELY TO FAIL", "🔴"),
         "likely to work": ("work", "#30a46c", "LIKELY TO WORK", "🟢"),
         "no-call": ("nocall", "#8b8d98", "NO-CALL", "⚪")}
EV_LABEL = {"known_resistance_mechanism": "Known resistance gene detected",
            "statistical_association_only": "Statistical association only",
            "no_known_signal": "No known resistance signal"}

uploaded = st.file_uploader("Upload a reconstructed, quality-checked genome (FASTA / .fna)",
                            type=["fna", "fasta", "fa", "txt"])

if uploaded is None:
    st.caption("Tip: BV-BRC *Klebsiella pneumoniae* genome FASTAs work well. "
               "Research prototype for demonstration.")
    st.stop()

with tempfile.NamedTemporaryFile(suffix=".fna", delete=False) as tmp:
    tmp.write(uploaded.read())
    fna_path = tmp.name

with st.spinner("Annotating genome with AMRFinderPlus and predicting…"):
    try:
        report = predict_report(fna_path, cfg)
    except FileNotFoundError:
        st.error("AMRFinderPlus not found. Activate the conda env and run `amrfinder --update`.")
        st.stop()
    except Exception as e:  # noqa: BLE001
        st.exception(e)
        st.stop()

genome_id = uploaded.name.rsplit(".", 1)[0]
results = report["results"]
n_fail = sum(r["call"] == "likely to fail" for r in results)
n_work = sum(r["call"] == "likely to work" for r in results)
n_nc = sum(r["call"] == "no-call" for r in results)

# ---- summary strip ----
st.markdown(f"""
<div class="gf-meta">
  <div><div class="lbl">Genome / isolate</div><div class="val">{genome_id}</div></div>
  <div><div class="lbl">Species</div><div class="val">{report['species']}</div></div>
  <div><div class="lbl">Predicted to fail</div><div class="val" style="color:#e5484d">{n_fail}</div></div>
  <div><div class="lbl">Predicted to work</div><div class="val" style="color:#30a46c">{n_work}</div></div>
  <div><div class="lbl">No-call</div><div class="val" style="color:#8b8d98">{n_nc}</div></div>
</div>
""", unsafe_allow_html=True)
st.caption(report["coverage_note"] + "  •  Genome scanned for known resistance determinants.")

# ---- result cards ----
cols = st.columns(len(results) or 1)
for col, res in zip(cols, results):
    klass, color, verdict, dot = STYLE.get(res["call"], ("nocall", "#8b8d98", res["call"], "⚪"))
    conf = res.get("confidence")
    conf_pct = f"{conf*100:.0f}%" if conf is not None else "—"
    ev = res.get("evidence_type", "")

    with col:
        html = [f'<div class="gf-card {klass}">']
        html.append(f'<div class="gf-drug">{dot} {res["antibiotic"]}</div>')
        html.append(f'<div class="gf-verdict {klass}">{verdict}</div>')
        if conf is not None:
            html.append(f'<div class="gf-small">confidence {conf_pct}</div>')
            html.append(f'<div class="gf-conf-track"><div class="gf-conf-fill" '
                        f'style="width:{conf*100:.0f}%;background:{color}"></div></div>')
        html.append(f'<div class="gf-small">p(resistant) = {res.get("prob_fail","—")}</div>')
        html.append(f'<div class="gf-small">Evidence: {EV_LABEL.get(ev,"—")}</div>')
        if res.get("detected_genes"):
            genes = ", ".join(g.split(":")[-1] for g in res["detected_genes"])
            html.append(f'<div class="gf-gene">🧬 Resistance gene(s): {genes}</div>')
        elif res["call"] == "likely to work":
            html.append('<div class="gf-none">No known resistance gene detected.</div>')
        elif ev == "statistical_association_only":
            sf = ", ".join(f.split(":")[-1] for f in res.get("statistical_features", [])) or "—"
            html.append(f'<div class="gf-stat">⚠ Statistical signal only: {sf}</div>')
        if res["call"] == "no-call" and res.get("nocall_reason"):
            html.append(f'<div class="gf-stat">No-call: {res["nocall_reason"]}</div>')
        html.append('</div>')
        st.markdown("".join(html), unsafe_allow_html=True)

        with st.expander("Why / details"):
            st.write(res.get("note", ""))
            if ev == "known_resistance_mechanism" and res.get("detected_genes"):
                st.write("**Mechanistic evidence** — curated resistance determinant(s): " +
                         ", ".join(g.split(":")[-1] for g in res["detected_genes"]))
            elif ev == "no_known_signal":
                st.write("No resistance determinant for this drug class was found by "
                         "AMRFinderPlus. The 'works' call reflects absence of known "
                         "resistance plus the model's learned pattern.")
            elif res.get("statistical_features"):
                st.write("Top statistical features (association, not proven cause): " +
                         ", ".join(f.split(":")[-1] for f in res["statistical_features"]))
            if res.get("prose"):
                st.write("Summary: " + res["prose"])
            tgt = ", ".join(DRUG_TARGETS.get(res["antibiotic"], []))
            gate = res.get("gate", "")
            gate_txt = {"target_present": f"drug target present ({tgt})",
                        "target_absent": f"drug target disrupted ({tgt})",
                        "unknown": "target status unknown"}.get(gate, gate)
            st.write(f"**Drug-target check:** {gate_txt}")

st.divider()
st.markdown(f'<div class="gf-banner">⚠️ {report["lab_banner"]}</div>', unsafe_allow_html=True)
st.caption("A no-call is a strength, not a failure — it flags weak, conflicting, or "
           "out-of-distribution evidence rather than forcing a false yes/no.")
