import bootstrap  # noqa: F401

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from app.ui_theme import apply_theme, BLUE_SCALE, TEAL_SCALE, BLUE_TEAL_SCALE, DISCRETE_PALETTE
from app.app_context import guard_page, sync_method_from_scenario
from app.sidebar_nav import render_sidebar
from sqlalchemy import text

from persistence.engine import get_engine
from persistence.repositories.alternative_repo import AlternativeRepo
from persistence.repositories.criterion_repo import CriterionRepo
from persistence.repositories.measurement_repo import MeasurementRepo
from persistence.repositories.preference_repo import PreferenceRepo
from services.vft_service import VFTService
from core.vft_model import Attribute

st.set_page_config(page_title="MCDA — Run VFT", layout="wide")
apply_theme()
st.title("Step 3: Run VFT Model")

engine = get_engine()
scenario_id = st.session_state.get("scenario_id")

if st.session_state.get("method_choice") != "vft":
    st.warning("This page is only for VFT scenarios.")
    st.switch_page("pages/1_decision_setup.py")

user_name = st.session_state.get("user_name", "")

if not scenario_id:
    st.warning("No scenario selected - go to Step 1.")
    if st.button("← Go to Step 1"):
        st.switch_page("pages/1_decision_setup.py")
    st.stop()

alt_repo = AlternativeRepo(engine)
crit_repo = CriterionRepo(engine)
meas_repo = MeasurementRepo(engine)
pref_repo = PreferenceRepo(engine)
vft_svc = VFTService(engine)

nav_left, nav_right = st.columns(2)
with nav_left:
    if st.button("← Step 3: Value Functions"):
        st.switch_page("pages/3b_vft_value_functions.py")
with nav_right:
    if st.button("Next: Results →", type="primary"):
        st.switch_page("pages/4_results.py")

st.caption("Preview the VFT scoring, then save to persist results.")
st.divider()

# Load data
existing_crit = crit_repo.list_by_scenario(scenario_id)
existing_alts = alt_repo.list_by_scenario(scenario_id)
matrix_df = meas_repo.load_matrix_ui(scenario_id)

if not existing_crit or not existing_alts:
    st.warning("No alternatives or criteria found. Complete Step 2 first.")
    st.stop()
if matrix_df.empty or matrix_df.isna().any().any():
    st.warning("Performance matrix is incomplete. Fill all values in Step 2.")
    st.stop()

# Load value functions
existing_vfs = vft_svc.load_value_functions(scenario_id)
alt_names = [a["name"] for a in existing_alts]
crit_names = [c["name"] for c in existing_crit]

# Build attribute objects
attributes = []
for crit in existing_crit:
    cname = crit["name"]
    vf = existing_vfs.get(cname, {})
    if not matrix_df.empty and cname in matrix_df.columns:
        data_min = float(matrix_df[cname].dropna().min())
        data_max = float(matrix_df[cname].dropna().max())
    else:
        data_min, data_max = 0.0, 100.0

    if vf:
        pts = sorted(vf.get("points", []), key=lambda p: p[0])
        ft = vf.get("function_type", "linear")
        if ft == "piecewise_linear":
            attr = Attribute(
                name=cname,
                min_val=data_min,
                max_val=data_max,
                scaling_type="Custom",
                custom_points=pts,
            )
        else:
            if len(pts) >= 2:
                min_val = float(pts[0][0])
                max_val = float(pts[-1][0])
                is_inc = float(pts[-1][1]) >= float(pts[0][1])
            else:
                min_val = data_min
                max_val = data_max
                is_inc = crit.get("direction") == "benefit"

            if max_val <= min_val:
                max_val = min_val + 1.0

            attr = Attribute(
                name=cname,
                min_val=min_val,
                max_val=max_val,
                scaling_type="Linear",
                scaling_direction="Increasing" if is_inc else "Decreasing",
            )
    else:
        is_inc = crit.get("direction") == "benefit"
        attr = Attribute(
            name=cname,
            min_val=data_min,
            max_val=data_max,
            scaling_type="Linear",
            scaling_direction="Increasing" if is_inc else "Decreasing",
        )
    attributes.append(attr)

# Preference set selection
with engine.begin() as conn:
    prefs = conn.execute(
        text("""
            SELECT preference_set_id::text AS preference_set_id, name
            FROM preference_sets WHERE scenario_id = :sid ORDER BY created_at DESC
        """),
        {"sid": scenario_id},
    ).mappings().all()
prefs = [dict(p) for p in prefs]

if not prefs:
    st.warning("No preference sets found. Go to Step 2 to create one.")
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
        key=f"pref_pick_vft_{scenario_id}",
    )
    pref_id = picked_pref[0] if picked_pref else pref_ids[0]
    st.session_state["preference_set_id"] = pref_id

with col_label:
    run_label = st.text_input(
        "Run label (optional)",
        value=st.session_state.get("run_label_default_vft", f"{pref_id_to_name.get(pref_id,'VFT')}-v1"),
    )
    st.session_state["run_label_default_vft"] = run_label

# Load weights
weights = pref_repo.load_weights_by_criterion_name(pref_id)
if not weights:
    st.warning("No weights found for this preference set. Go to Step 2 and save weights.")
    st.stop()

# Set weights on attributes
w_total = sum(float(weights.get(c.name, 0.0)) for c in attributes)
for attr in attributes:
    w_raw = float(weights.get(attr.name, 0.0))
    attr.weight = w_raw / w_total if w_total > 0 else 1.0 / len(attributes)
    attr.swing_weight = attr.weight * 100

# Preview computation
def compute_preview():
    utility_matrix = {}
    weighted_matrix = {}
    total_scores = {}
    attr_by_name = {a.name: a for a in attributes}

    for alt_name in matrix_df.index:
        utility_matrix[alt_name] = {}
        weighted_matrix[alt_name] = {}
        total = 0.0
        for crit_name in matrix_df.columns:
            raw = float(matrix_df.loc[alt_name, crit_name])
            attr = attr_by_name.get(crit_name)
            u = attr.get_value(raw) if attr else 0.0
            w = float(weights.get(crit_name, 0.0))
            if w_total > 0:
                w = w / w_total
            utility_matrix[alt_name][crit_name] = u
            weighted_matrix[alt_name][crit_name] = u * w
            total += u * w
        total_scores[alt_name] = total

    return utility_matrix, weighted_matrix, total_scores

st.divider()
st.subheader("Run Preview")

if st.button("▶ Preview VFT Scoring", type="primary"):
    utility_matrix, weighted_matrix, total_scores = compute_preview()
    st.session_state["vft_preview"] = {
        "utility_matrix": utility_matrix,
        "weighted_matrix": weighted_matrix,
        "total_scores": total_scores,
    }
    st.rerun()

if st.button("✕ Clear Preview"):
    st.session_state.pop("vft_preview", None)
    st.rerun()

preview = st.session_state.get("vft_preview")

if preview:
    total_scores = preview["total_scores"]
    utility_matrix = preview["utility_matrix"]
    weighted_matrix = preview["weighted_matrix"]

    sorted_alts = sorted(total_scores.items(), key=lambda x: x[1], reverse=True)

    st.subheader("Preview Ranking")
    rank_df = pd.DataFrame([
        {"Rank": i + 1, "Alternative": alt, "VFT Score": f"{sc:.4f}"}
        for i, (alt, sc) in enumerate(sorted_alts)
    ])

    bar_fig = px.bar(
        pd.DataFrame({"Alternative": [x[0] for x in sorted_alts], "Score": [x[1] for x in sorted_alts]}),
        x="Alternative", y="Score",
        color="Score", color_continuous_scale="Greens",
        title="VFT Total Score Preview",
    )
    bar_fig.update_layout(height=380)
    st.plotly_chart(bar_fig, use_container_width=True)

    st.dataframe(rank_df, use_container_width=True, hide_index=True)

    st.subheader("Utility Matrix (0-1)")
    util_df = pd.DataFrame(utility_matrix).T
    util_df = util_df[crit_names]
    st.dataframe(util_df.style.format("{:.4f}"), use_container_width=True)

    st.subheader("Weighted Contribution Matrix")
    weighted_df = pd.DataFrame(weighted_matrix).T
    weighted_df = weighted_df[crit_names]
    weighted_df["Total"] = weighted_df.sum(axis=1)
    st.dataframe(weighted_df.style.format("{:.4f}"), use_container_width=True)

    # Criterion contribution chart
    st.subheader("Contribution by Criterion")
    contrib_long = weighted_df.drop(columns=["Total"]).reset_index().melt(
        id_vars="index", var_name="Criterion", value_name="Contribution"
    ).rename(columns={"index": "Alternative"})

    stack_fig = px.bar(
        contrib_long,
        x="Alternative",
        y="Contribution",
        color="Criterion",
        title="Weighted Score Composition by Alternative",
    )
    stack_fig.update_layout(barmode="stack", height=420)
    st.plotly_chart(stack_fig, use_container_width=True)

    st.divider()
    st.subheader("Save Run")

    if st.button("💾 Save VFT Run", type="primary"):
        alt_map = {a["name"]: a["alternative_id"] for a in existing_alts}
        crit_map = {c["name"]: c["criterion_id"] for c in existing_crit}
        normalized_weights = {
            crit_name: (float(weights.get(crit_name, 0.0)) / w_total if w_total > 0 else 0.0)
            for crit_name in crit_names
        }

        run_id = vft_svc.run_and_persist(
            scenario_id=scenario_id,
            preference_set_id=pref_id,
            executed_by=user_name or None,
            matrix_df=matrix_df,
            weights=normalized_weights,
            attributes=attributes,
            alt_map=alt_map,
            crit_map=crit_map,
            run_label=run_label or None,
        )

        st.success(f"✅ VFT run saved successfully. Run ID: {str(run_id)[:8]}…")
        st.session_state["last_run_id"] = str(run_id)
        st.session_state["latest_run_method"] = "vft"
        st.session_state["latest_run_label"] = run_label
        st.session_state.pop("vft_preview", None)
        st.switch_page("pages/4_results.py")

else:
    st.info("Click **Preview VFT Scoring** to compute the VFT utilities and total scores.")

st.divider()
col_prev, col_next = st.columns(2)
with col_prev:
    if st.button("← Back to Value Functions", key="vft_run_back_bottom"):
        st.switch_page("pages/3b_vft_value_functions.py")
with col_next:
    if st.button("Go to Results →", key="vft_run_results_bottom"):
        st.switch_page("pages/4_results.py")
