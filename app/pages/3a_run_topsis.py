import bootstrap  # noqa: F401

import hashlib
import numpy as np
import pandas as pd
import streamlit as st
from app.app_context import guard_page, sync_method_from_scenario
from app.sidebar_nav import render_sidebar
from sqlalchemy import text

from core.topsis import compute_topsis
from persistence.engine import get_engine
from services.scenario_service import ScenarioService
from persistence.repositories.measurement_repo import MeasurementRepo
from persistence.repositories.preference_repo import PreferenceRepo
from persistence.repositories.result_repo import ResultRepo
from persistence.repositories.topsis_repo import TopsisRepo

st.set_page_config(page_title="MCDA — Run TOPSIS", layout="wide")
st.title("Step 3: Run TOPSIS Model")

guard_page("pages/3a_run_topsis.py", require_scenario=True)
sync_method_from_scenario()
render_sidebar("pages/3a_run_topsis.py")

ENGINE_VERSION = "core=0.1.0"

engine = get_engine()
scenario_id = st.session_state.get("scenario_id")

if st.session_state.get("method_choice") != "topsis":
    st.warning("This page is only for TOPSIS scenarios.")
    st.switch_page("pages/1_decision_setup.py")

user_name = st.session_state.get("user_name", "")

if not scenario_id:
    st.warning("No scenario selected — go to Step 1.")
    if st.button("← Go to Step 1"):
        st.switch_page("pages/1_decision_setup.py")
    st.stop()

# Navigation
nav_left, nav_right = st.columns(2)
with nav_left:
    if st.button("← Step 2: Data Input"):
        st.switch_page("pages/2_data_input.py")
with nav_right:
    if st.button("Next: Results →", type="primary"):
        st.switch_page("pages/4_results.py")

st.caption("Preview the TOPSIS run against your data, then save to persist results.")
st.divider()

# Preference set selection
with engine.begin() as conn:
    prefs = conn.execute(
        text("""
            SELECT preference_set_id::text AS preference_set_id, name, type, status, created_at
            FROM preference_sets WHERE scenario_id = :sid ORDER BY created_at DESC
        """),
        {"sid": scenario_id},
    ).mappings().all()
prefs = [dict(p) for p in prefs]

if not prefs:
    st.warning("No preference sets found. Go to Step 2 and create one with weights.")
    st.stop()

pref_ids = [p["preference_set_id"] for p in prefs]
pref_id_to_name = {p["preference_set_id"]: p["name"] for p in prefs}

default_pref = st.session_state.get("preference_set_id") or pref_ids[0]
if default_pref not in pref_ids:
    default_pref = pref_ids[0]

col_pref, col_label = st.columns(2)
with col_pref:
    picked_pref = st.multiselect(
        "Preference set",
        options=pref_ids,
        default=[default_pref],
        max_selections=1,
        format_func=lambda x: pref_id_to_name.get(x, x),
        key=f"pref_pick_step3_{scenario_id}",
    )
    pref_id = picked_pref[0] if picked_pref else pref_ids[0]
    st.session_state["preference_set_id"] = pref_id

with col_label:
    default_label = f"{pref_id_to_name.get(pref_id, 'Run')}-v1"
    run_label = st.text_input(
        "Run label (optional)",
        value=st.session_state.get("run_label_default", default_label),
        placeholder="e.g. BaseCase-v1, CostFocus-v2",
    )
    st.session_state["run_label_default"] = run_label

scenario_service = ScenarioService(engine)
result_repo = ResultRepo(engine)
topsis_repo = TopsisRepo(engine)

# Load + validate
preview_key = f"{scenario_id}|{pref_id}|topsis"
if st.session_state.get("preview_key") != preview_key:
    st.session_state["preview_key"] = preview_key
    st.session_state.pop("topsis_preview", None)
    st.session_state.pop("dup_check", None)

try:
    data = scenario_service.load(scenario_id, pref_id)
    ok, issues = scenario_service.validate(data)
except Exception as e:
    st.error(str(e))
    st.stop()

st.subheader("Validation")
if ok:
    st.success("✅ Scenario data is complete and ready to run.")
else:
    for msg in issues:
        st.error(msg)
    st.stop()

# Input summary
with st.expander("View input summary", expanded=False):
    meas_repo = MeasurementRepo(engine)
    pref_repo = PreferenceRepo(engine)
    mat = meas_repo.load_matrix_ui(scenario_id)
    wts = pref_repo.load_weights_by_criterion_name(pref_id)
    if not mat.empty:
        wt_row = pd.DataFrame([{c: wts.get(c, 0.0) for c in mat.columns}], index=["Weight"])
        st.dataframe(pd.concat([wt_row, mat]), use_container_width=True)

def compute_input_signature() -> str:
    w = data.weights.astype(float)
    w = w / (float(w.sum()) + 1e-12)
    mat = np.round(data.matrix.astype(float), 12)
    w = np.round(w, 12)
    h = hashlib.sha256()
    h.update(("alts:" + "|".join(data.alternative_ids)).encode())
    h.update(("crits:" + "|".join(data.criterion_ids)).encode())
    h.update(("dirs:" + "|".join(data.directions)).encode())
    h.update(mat.tobytes(order="C"))
    h.update(w.tobytes(order="C"))
    return h.hexdigest()

def find_existing_identical_run(sig: str):
    with engine.begin() as conn:
        row = conn.execute(
            text("""
                SELECT run_id::text AS run_id, executed_at, executed_by, run_label
                FROM runs
                WHERE scenario_id = :sid AND preference_set_id = :pid
                  AND method = 'topsis' AND input_signature = :sig
                ORDER BY executed_at DESC LIMIT 1
            """),
            {"sid": scenario_id, "pid": pref_id, "sig": sig},
        ).mappings().first()
    if not row:
        return None, None
    return str(row["run_id"]), dict(row)

st.divider()
st.subheader("Run Preview")

colA, colB = st.columns(2)
with colA:
    run_preview = st.button("▶ Preview Run", type="primary")
with colB:
    if st.button("✕ Clear Preview"):
        st.session_state.pop("topsis_preview", None)
        st.session_state.pop("dup_check", None)
        st.rerun()

if run_preview:
    sig = compute_input_signature()
    w = data.weights.astype(float)
    w = w / (float(w.sum()) + 1e-12)
    artifacts = compute_topsis(
        matrix=data.matrix.astype(float),
        weights=w,
        directions=data.directions,
    )
    alt_scores = sorted(
        [{"alternative_name": data.alternative_names[i], "score": float(artifacts.c_star[i])}
         for i in range(len(data.alternative_names))],
        key=lambda r: r["score"], reverse=True,
    )
    for i, r in enumerate(alt_scores, 1):
        r["rank"] = i

    existing_run_id, existing_meta = find_existing_identical_run(sig)
    st.session_state["dup_check"] = {"sig": sig, "existing_run_id": existing_run_id, "existing_meta": existing_meta}
    st.session_state["topsis_preview"] = {"sig": sig, "scores": alt_scores, "artifacts": artifacts}
    st.rerun()

import pandas as pd
import plotly.express as px
preview = st.session_state.get("topsis_preview")
dup_check = st.session_state.get("dup_check")

if preview:
    st.subheader("Preview Ranking")
    scores_df = pd.DataFrame(preview["scores"])
    import plotly.express as px
    fig = px.bar(
        scores_df.sort_values("rank"),
        x="alternative_name", y="score",
        color="score", color_continuous_scale="Blues",
        title="TOPSIS Score C* Preview",
        labels={"alternative_name": "Alternative", "score": "C* Score"},
    )
    fig.update_layout(showlegend=False, height=340, margin=dict(l=10,r=10,t=40,b=10))
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(scores_df, use_container_width=True)

st.divider()
st.subheader("Save Results")

save_disabled = preview is None
overwrite = False

if preview and dup_check and dup_check.get("existing_run_id"):
    meta = dup_check.get("existing_meta") or {}
    st.warning("⚠ Identical run already exists (same matrix + weights fingerprint).")
    st.caption(f"Existing run: {dup_check['existing_run_id'][:8]}… by {meta.get('executed_by','?')} at {str(meta.get('executed_at','?'))[:16]}")
    overwrite = st.checkbox("Overwrite existing run instead of creating a new one", value=True)

if st.button("💾 Save Results to Database", type="primary", disabled=save_disabled):
    if preview is None:
        st.error("Run a preview first.")
        st.stop()

    current_sig = compute_input_signature()
    if preview.get("sig") != current_sig:
        st.error("Inputs changed since preview — run preview again.")
        st.stop()

    artifacts = preview["artifacts"]
    sig = preview["sig"]
    label_clean = (run_label or "").strip() or None
    existing_run_id = dup_check.get("existing_run_id") if dup_check else None

    def persist(run_id):
        topsis_repo.save_run_config(run_id, normalization="vector", distance="euclidean")
        alt_id_to_score = {data.alternative_ids[i]: float(artifacts.c_star[i]) for i in range(len(data.alternative_ids))}
        result_repo.replace_scores(run_id, alt_id_to_score)
        m, n = data.matrix.shape
        norm_rows, w_rows, ideal_rows, dist_rows = [], [], [], []
        for i in range(m):
            for j in range(n):
                norm_rows.append({"run_id": run_id, "alternative_id": data.alternative_ids[i],
                                  "criterion_id": data.criterion_ids[j], "value": float(artifacts.normalized_matrix[i,j])})
                w_rows.append({"run_id": run_id, "alternative_id": data.alternative_ids[i],
                               "criterion_id": data.criterion_ids[j], "value": float(artifacts.weighted_matrix[i,j])})
        for j in range(n):
            ideal_rows.append({"run_id": run_id, "criterion_id": data.criterion_ids[j],
                               "pos_ideal": float(artifacts.pis[j]), "neg_ideal": float(artifacts.nis[j])})
        for i in range(m):
            dist_rows.append({"run_id": run_id, "alternative_id": data.alternative_ids[i],
                              "s_pos": float(artifacts.s_pos[i]), "s_neg": float(artifacts.s_neg[i]),
                              "c_star": float(artifacts.c_star[i])})
        topsis_repo.replace_normalized(run_id, norm_rows)
        topsis_repo.replace_weighted(run_id, w_rows)
        topsis_repo.replace_ideals(run_id, ideal_rows)
        topsis_repo.replace_distances(run_id, dist_rows)

    if existing_run_id and overwrite:
        with engine.begin() as conn:
            conn.execute(
                text("""
                    UPDATE runs SET executed_at=now(), executed_by=:by,
                        engine_version=:ev, input_signature=:sig, run_label=:lbl
                    WHERE run_id=:rid
                """),
                {"by": user_name, "ev": ENGINE_VERSION, "sig": sig, "lbl": label_clean, "rid": existing_run_id},
            )
        persist(existing_run_id)
        run_id = existing_run_id
        st.success(f"✅ Updated existing run: {run_id[:8]}…")
    else:
        with engine.begin() as conn:
            row = conn.execute(
                text("""
                    INSERT INTO runs (scenario_id, preference_set_id, method, engine_version,
                                     executed_by, input_signature, run_label)
                    VALUES (:sid, :pid, 'topsis', :ev, :by, :sig, :lbl)
                    RETURNING run_id::text AS run_id
                """),
                {"sid": scenario_id, "pid": pref_id, "ev": ENGINE_VERSION,
                 "by": user_name, "sig": sig, "lbl": label_clean},
            ).mappings().first()
        run_id = str(row["run_id"])
        persist(run_id)
        st.success(f"✅ Saved new run: {run_id[:8]}…")

    st.session_state["last_run_id"] = run_id
    st.session_state.pop("topsis_preview", None)
    st.session_state.pop("dup_check", None)
    st.toast("✅ TOPSIS run saved! Redirecting to Results…", icon="🏆")
    st.switch_page("pages/4_results.py")
