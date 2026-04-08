import bootstrap  # noqa: F401

import pandas as pd
import streamlit as st
from app.ui_theme import apply_theme, BLUE_SCALE, TEAL_SCALE, BLUE_TEAL_SCALE, DISCRETE_PALETTE, section_header
from app.app_context import guard_page, sync_method_from_scenario
from app.sidebar_nav import render_sidebar
from sqlalchemy import text
import plotly.express as px
import plotly.graph_objects as go

from persistence.engine import get_engine
from persistence.repositories.measurement_repo import MeasurementRepo
from persistence.repositories.preference_repo import PreferenceRepo
from persistence.repositories.run_repo import RunRepo
from persistence.repositories.result_repo import ResultRepo
from persistence.repositories.topsis_read_repo import TopsisReadRepo
from services.vft_service import VFTService

st.set_page_config(page_title="MCDA — Results", layout="wide")
apply_theme()
st.title("Step 4: Results")
st.markdown(
    """
    <style>
    .results-header-grid {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 24px;
      align-items: center;
      background: #FFFFFF;
      border: 1px solid #E2E8F0;
      border-radius: 10px;
      padding: 12px 20px;
      margin: 8px 0 10px 0;
      box-shadow: 0 1px 2px rgba(0,0,0,0.05);
    }
    .results-header-item .lbl {
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 0.45px;
      font-weight: 500;
      color: #64748B;
      line-height: 1.2;
      margin-bottom: 3px;
    }
    .results-header-item .val {
      font-size: 15px;
      font-weight: 600;
      color: #1E293B;
      line-height: 1.3;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    .results-divider {
      height: 1px;
      background: #E2E8F0;
      margin: 12px 0 14px 0;
    }
    .run-form-section {
      max-width: 900px;
      margin: 0 auto 10px auto;
      padding: 16px 20px;
      background: #FFFFFF;
      border: 1px solid #E2E8F0;
      border-radius: 10px;
      box-shadow: 0 1px 2px rgba(0,0,0,0.04);
    }
    .run-form-row {
      display: grid;
      grid-template-columns: 140px 1fr;
      gap: 16px;
      align-items: center;
      margin-bottom: 10px;
    }
    .run-form-row:last-child {
      margin-bottom: 0;
    }
    .run-form-label {
      font-size: 14px;
      font-weight: 600;
      color: #334155;
      font-family: Inter, "Open Sans", sans-serif;
      line-height: 1.3;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

guard_page("pages/4_results.py", require_scenario=True)
sync_method_from_scenario()
render_sidebar("pages/4_results.py")

engine = get_engine()
run_repo = RunRepo(engine)
result_repo = ResultRepo(engine)
topsis_read = TopsisReadRepo(engine)
meas_repo = MeasurementRepo(engine)
pref_repo = PreferenceRepo(engine)
vft_svc = VFTService(engine)

nav_left, nav_right = st.columns(2)
with nav_left:
    if st.button("← Back"):
        st.switch_page("pages/3_run_models.py")
with nav_right:
    if st.button("Next: Sensitivity Analysis →", type="primary"):
        st.switch_page("pages/5_sensitivity.py")

st.caption("View detailed results for any saved run.")
st.divider()

# ─── Selectors ────────────────────────────────────────────────────────────────
section_header("Select Run to View", variant="gradient")


def _inline_single_pick(label: str, options: list[str], default_value: str, format_func, key: str) -> str:
    col_label, col_input = st.columns([1, 6])
    with col_label:
        st.markdown(f"<div class='run-form-label'>{label}</div>", unsafe_allow_html=True)
    with col_input:
        picked = st.multiselect(
            label,
            options=options,
            default=[default_value] if default_value in options else [options[0]],
            max_selections=1,
            format_func=format_func,
            key=key,
            label_visibility="collapsed",
        )
    return picked[0] if picked else options[0]

with engine.begin() as conn:
    decisions = conn.execute(
        text("SELECT decision_id::text, title FROM decisions ORDER BY created_at DESC LIMIT 200")
    ).mappings().all()
decisions = [dict(d) for d in decisions]

if not decisions:
    st.warning("No decisions found. Create one in Step 1.")
    st.stop()

decision_ids = [d["decision_id"] for d in decisions]
dec_id_to_title = {d["decision_id"]: d["title"] for d in decisions}

default_dec = st.session_state.get("decision_id") or decision_ids[0]
decision_id = _inline_single_pick(
    "Decision",
    decision_ids,
    default_dec,
    lambda x: dec_id_to_title.get(x, x),
    "pick_decision_step4",
)
st.session_state["decision_id"] = decision_id

with engine.begin() as conn:
    scenarios = conn.execute(
        text("""
            SELECT scenario_id::text, name, method_type FROM scenarios
            WHERE decision_id = :did ORDER BY created_at DESC LIMIT 200
        """),
        {"did": decision_id},
    ).mappings().all()
scenarios = [dict(s) for s in scenarios]

if not scenarios:
    st.warning("No scenarios under this decision.")
    st.stop()

scen_ids = [s["scenario_id"] for s in scenarios]
scen_id_to_name = {s["scenario_id"]: s["name"] for s in scenarios}
scen_id_to_method = {s["scenario_id"]: s.get("method_type", "topsis") for s in scenarios}

default_scen = st.session_state.get("scenario_id")
if default_scen not in scen_ids:
    default_scen = scen_ids[0]

scenario_id = _inline_single_pick(
    "Scenario",
    scen_ids,
    default_scen,
    lambda x: scen_id_to_name.get(x, x),
    f"pick_scenario_step4_{decision_id}",
)
st.session_state["scenario_id"] = scenario_id
st.session_state["method_choice"] = scen_id_to_method.get(scenario_id, "topsis")

with engine.begin() as conn:
    prefs = conn.execute(
        text("""
            SELECT preference_set_id::text, name FROM preference_sets
            WHERE scenario_id = :sid ORDER BY created_at DESC
        """),
        {"sid": scenario_id},
    ).mappings().all()
prefs = [dict(p) for p in prefs]

if not prefs:
    st.warning("No preference sets found.")
    st.stop()

pref_ids = [p["preference_set_id"] for p in prefs]
pref_id_to_name = {p["preference_set_id"]: p["name"] for p in prefs}

default_pref = st.session_state.get("preference_set_id")
if default_pref not in pref_ids:
    default_pref = pref_ids[0]

pref_id = _inline_single_pick(
    "Preference Set",
    pref_ids,
    default_pref,
    lambda x: pref_id_to_name.get(x, x),
    f"pref_pick_step4_{scenario_id}",
)
st.session_state["preference_set_id"] = pref_id

with engine.begin() as conn:
    runs = conn.execute(
        text("""
            SELECT run_id::text, method, executed_at, executed_by, run_label
            FROM runs WHERE scenario_id = :sid AND preference_set_id = :pid
            ORDER BY executed_at DESC LIMIT 200
        """),
        {"sid": scenario_id, "pid": pref_id},
    ).mappings().all()
runs = [dict(r) for r in runs]

if not runs:
    st.warning("No runs found for this scenario + preference set.")
    st.stop()

run_ids = [r["run_id"] for r in runs]
run_id_to_row = {r["run_id"]: r for r in runs}

def run_label_fmt(rid):
    r = run_id_to_row.get(rid, {})
    lbl = (r.get("run_label") or "").strip()
    by = f" · {r['executed_by']}" if r.get("executed_by") else ""
    ts = str(r.get("executed_at", ""))[:16]
    method_tag = r.get("method", "").upper()
    base = f"[{method_tag}] {ts}{by}"
    return f"{lbl} | {base}" if lbl else base

default_run = st.session_state.get("last_run_id")
if default_run not in run_ids:
    default_run = run_ids[0]

run_id = _inline_single_pick(
    "Run",
    run_ids,
    default_run,
    run_label_fmt,
    f"run_pick_step4_{scenario_id}_{pref_id}",
)
st.session_state["last_run_id"] = run_id

current_run = run_id_to_row.get(run_id, {})
current_method = current_run.get("method", "topsis")

# ─── Run Summary ──────────────────────────────────────────────────────────────
lbl = current_run.get("run_label") or "—"
st.markdown(
    f"""
    <div class="results-header-grid">
      <div class="results-header-item">
        <div class="lbl">Method</div>
        <div class="val">{current_method.upper()}</div>
      </div>
      <div class="results-header-item">
        <div class="lbl">Run By</div>
        <div class="val">{current_run.get("executed_by") or "—"}</div>
      </div>
      <div class="results-header-item">
        <div class="lbl">Run At</div>
        <div class="val">{str(current_run.get("executed_at", "—"))[:16]}</div>
      </div>
      <div class="results-header-item">
        <div class="lbl">Label</div>
        <div class="val">{lbl}</div>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)
st.markdown("<div class='results-divider'></div>", unsafe_allow_html=True)

# ─── Inputs table ─────────────────────────────────────────────────────────────
with st.expander("📊 Inputs Used for This Run", expanded=False):
    matrix_df = meas_repo.load_matrix_ui(scenario_id)
    weights_map = pref_repo.load_weights_by_criterion_name(pref_id)
    if matrix_df is not None and not matrix_df.empty:
        crit_cols = list(matrix_df.columns)
        wt_row = {c: float(weights_map.get(c, 0.0)) for c in crit_cols}
        wt_df = pd.DataFrame([wt_row], index=["Weight"])
        combined = pd.concat([wt_df, matrix_df])
        st.dataframe(combined.style.format("{:.4f}"), use_container_width=True)
        st.download_button("⬇ Matrix + Weights CSV",
                           data=combined.to_csv().encode(),
                           file_name=f"inputs_{run_id[:8]}.csv", mime="text/csv")

st.markdown("<div class='results-divider'></div>", unsafe_allow_html=True)

# ─── Results: Branch on method ────────────────────────────────────────────────
scores = result_repo.get_scores_with_names(run_id)
scores_df = pd.DataFrame(scores)

if current_method == "topsis":
    dist_df = topsis_read.get_distances(run_id)
    ideals_df = topsis_read.get_ideals(run_id)
    norm_df = topsis_read.get_matrix(run_id, "normalized")
    w_df = topsis_read.get_matrix(run_id, "weighted")

    tab_rank, tab_dist, tab_ideals, tab_norm, tab_weighted = st.tabs([
        "🏆 Ranking", "📐 Distances", "🎯 Ideals (PIS/NIS)", "📋 Normalized", "⚖️ Weighted"
    ])

    with tab_rank:
        st.subheader("Final Ranking")
        if not scores_df.empty:
            fig = px.bar(
                scores_df.sort_values("rank"),
                x="alternative_name", y="score",
                color="score", color_continuous_scale=BLUE_SCALE,
                title="TOPSIS Score C* by Alternative",
                labels={"alternative_name": "Alternative", "score": "C* Score"},
            )
            fig.update_layout(showlegend=False, height=360, margin=dict(l=10,r=10,t=36,b=10))
            st.plotly_chart(fig, use_container_width=True)
            st.caption("""
**Fig: TOPSIS Ranking Bar Chart** — Each bar represents a C* score (Closeness to Ideal) 
for an alternative. Higher = better. C* = S−/(S+ + S−) where S+ is distance to ideal best
and S− is distance to ideal worst.
            """)
            st.info("💡 **Note:** C* scores near 1.0 indicate the alternative is closest to the ideal best solution. "
                    "Alternatives with similar scores are close in performance; check distance plots for nuance.")
            st.dataframe(scores_df, use_container_width=True)
            st.download_button("⬇ Ranking CSV", data=scores_df.to_csv(index=False).encode(),
                               file_name=f"ranking_{run_id[:8]}.csv", mime="text/csv")

    with tab_dist:
        st.subheader("Separation Measures (S+, S−, C*)")
        if dist_df is not None and not dist_df.empty:
            fig_sc = px.scatter(
                dist_df, x="s_pos", y="s_neg", text="alternative",
                hover_data=["c_star"],
                title="S+ vs S− (lower S+, higher S− is better)",
                labels={"s_pos": "S+ (distance to ideal best)", "s_neg": "S− (distance to ideal worst)"},
            )
            fig_sc.update_traces(textposition="top center")
            fig_sc.update_layout(height=380, margin=dict(l=10,r=10,t=42,b=10))
            st.plotly_chart(fig_sc, use_container_width=True)
            st.caption("""
**Fig: S+ vs S− Scatter Plot** — Each point is an alternative. The best alternatives 
appear in the lower-right (low S+, high S−). Alternatives in the upper-left 
are far from ideal best and close to ideal worst.
            """)
            st.info("💡 **Note:** Alternatives clustered near each other in this plot have similar trade-off profiles. "
                    "Outliers may indicate a strongly dominant or dominated option.")
            st.dataframe(dist_df, use_container_width=True)
            st.download_button("⬇ Distances CSV", data=dist_df.to_csv(index=False).encode(),
                               file_name=f"distances_{run_id[:8]}.csv", mime="text/csv")

    with tab_ideals:
        st.subheader("Ideal Points (PIS/NIS) per Criterion")
        if ideals_df is not None and not ideals_df.empty:
            st.dataframe(ideals_df, use_container_width=True)
            st.caption("**PIS** = Positive Ideal Solution (best weighted value per criterion). **NIS** = Negative Ideal Solution (worst value).")

            # Valve view
            if w_df is not None and not w_df.empty:
                ideals_map = ideals_df.set_index("criterion")[["pos_ideal", "neg_ideal"]].to_dict(orient="index")
                weights_map2 = pref_repo.load_weights_by_criterion_name(pref_id)
                for c in list(w_df.columns):
                    w_c = float(weights_map2.get(c, 0.0))
                    pos = float(ideals_map.get(c, {}).get("pos_ideal", 0))
                    neg = float(ideals_map.get(c, {}).get("neg_ideal", 0))
                    with st.expander(f"Valve View: {c} (weight={w_c:.3f})", expanded=False):
                        df_c = pd.DataFrame({"alternative": list(w_df.index), "weighted_value": w_df[c].values})
                        df_c = df_c.sort_values("weighted_value", ascending=False)
                        fig = go.Figure()
                        fig.add_trace(go.Scatter(
                            x=df_c["weighted_value"], y=df_c["alternative"],
                            mode="markers+text", text=[f"{v:.4f}" for v in df_c["weighted_value"]],
                            textposition="middle right", name="Alternative",
                            marker=dict(color="#1D4ED8", size=10),
                        ))
                        fig.add_vline(x=pos, line_dash="solid", line_color="#0F766E", annotation_text="PIS")
                        fig.add_vline(x=neg, line_dash="dash", line_color="#2563EB", annotation_text="NIS")
                        xmin = min(df_c["weighted_value"].min(), pos, neg)
                        xmax = max(df_c["weighted_value"].max(), pos, neg)
                        pad = (xmax - xmin) * 0.1 if xmax > xmin else 0.1
                        fig.update_xaxes(range=[xmin - pad, xmax + pad])
                        fig.update_layout(title=f"Valve View: {c}", height=350, margin=dict(l=10,r=10,t=42,b=10))
                        st.plotly_chart(fig, use_container_width=True)
                        st.caption(f"**Fig: Valve View for {c}** — Solid line = PIS (ideal best weighted value), dashed = NIS (ideal worst). "
                                   "Alternatives are plotted along the weighted value axis.")

    with tab_norm:
        st.subheader("Normalized Matrix")
        if norm_df is not None and not norm_df.empty:
            fig_heat = px.imshow(norm_df.values, x=list(norm_df.columns), y=list(norm_df.index),
                                 aspect="auto", title="Normalized Matrix Heatmap",
                                 color_continuous_scale=BLUE_SCALE)
            fig_heat.update_layout(height=350, margin=dict(l=10,r=10,t=42,b=10))
            st.plotly_chart(fig_heat, use_container_width=True)
            st.caption("**Fig: Normalized Matrix Heatmap** — Vector-normalized values. Darker = higher normalized value.")
            st.dataframe(norm_df, use_container_width=True)
            st.download_button("⬇ Normalized CSV", data=norm_df.to_csv().encode(),
                               file_name=f"normalized_{run_id[:8]}.csv", mime="text/csv")

    with tab_weighted:
        st.subheader("Weighted Normalized Matrix")
        if w_df is not None and not w_df.empty:
            fig_heat2 = px.imshow(w_df.values, x=list(w_df.columns), y=list(w_df.index),
                                  aspect="auto", title="Weighted Matrix Heatmap",
                                  color_continuous_scale=BLUE_TEAL_SCALE)
            fig_heat2.update_layout(height=350, margin=dict(l=10,r=10,t=42,b=10))
            st.plotly_chart(fig_heat2, use_container_width=True)
            st.caption("**Fig: Weighted Matrix Heatmap** — Normalized values multiplied by criterion weights. "
                       "Reflects both data and weight preferences.")
            st.dataframe(w_df, use_container_width=True)
            st.download_button("⬇ Weighted CSV", data=w_df.to_csv().encode(),
                               file_name=f"weighted_{run_id[:8]}.csv", mime="text/csv")

elif current_method == "vft":
    vft_data = vft_svc.get_vft_results(run_id, engine)
    scores_list = vft_data.get("scores", [])
    utilities_list = vft_data.get("utilities", [])
    weighted_list = vft_data.get("weighted", [])

    tab_rank, tab_util, tab_contrib = st.tabs(["🏆 Ranking", "📊 Utilities", "🧩 Contributions"])

    with tab_rank:
        st.subheader("VFT Final Ranking")
        if scores_list:
            sc_df = pd.DataFrame(scores_list)
            fig = px.bar(
                sc_df.sort_values("rank"),
                x="alternative_name", y="score",
                color="score", color_continuous_scale=BLUE_TEAL_SCALE,
                title="VFT Total Score by Alternative",
                labels={"alternative_name": "Alternative", "score": "Total Score"},
            )
            fig.update_layout(showlegend=False, height=360, margin=dict(l=10,r=10,t=36,b=10))
            st.plotly_chart(fig, use_container_width=True)
            st.caption("""
**Fig: VFT Ranking Bar Chart** — Total scores are the weighted sum of utility values 
u(x) ∈ [0,1] for each criterion. Higher = better. Score = Σ(weight_i × utility_i(x_i)).
            """)
            st.info("💡 **Note:** VFT scores are sensitive to value function shape. "
                    "Small changes in the breakpoints can shift rankings — review your value functions in Step 3b.")
            st.dataframe(sc_df, use_container_width=True, hide_index=True)

    with tab_util:
        st.subheader("Utility Matrix")
        if utilities_list:
            util_df = pd.DataFrame(utilities_list)
            util_wide = util_df.pivot(index="alternative_name", columns="criterion_name", values="utility_value")
            fig_heat = px.imshow(util_wide.values, x=list(util_wide.columns), y=list(util_wide.index),
                                 aspect="auto", title="Utility Values Heatmap (0=worst, 1=best)",
                                 color_continuous_scale=BLUE_TEAL_SCALE, zmin=0, zmax=1)
            fig_heat.update_layout(height=360, margin=dict(l=10,r=10,t=42,b=10))
            st.plotly_chart(fig_heat, use_container_width=True)
            st.caption("**Fig: Utility Heatmap** — Darker teal-blue cells indicate higher utility (close to 1), while lighter blue cells indicate lower utility (close to 0). "
                       "Each cell shows how well an alternative performs on a criterion after value function transformation.")
            st.dataframe(util_wide, use_container_width=True)

    with tab_contrib:
        st.subheader("Weighted Utility Contributions")
        if weighted_list:
            w_df_vft = pd.DataFrame(weighted_list)
            fig_stacked = px.bar(
                w_df_vft, x="alternative_name", y="weighted_utility", color="criterion_name",
                title="Score Contribution by Criterion",
                barmode="stack",
                labels={"alternative_name": "Alternative", "weighted_utility": "Weighted Utility",
                        "criterion_name": "Criterion"},
                color_discrete_sequence=DISCRETE_PALETTE,
            )
            fig_stacked.update_layout(height=380, margin=dict(l=10,r=10,t=42,b=10))
            st.plotly_chart(fig_stacked, use_container_width=True)
            st.caption("""
**Fig: Stacked Contribution Chart** — Each segment shows the weighted utility contribution of one 
criterion to the total score. Tall segments = high contribution (high utility × high weight).
            """)
            st.info(
                "💡 **Note:** Criteria with short segments may be less influential due to low weight or "
                "low utility scores. Consider reviewing weights if the intended priorities are not reflected."
            )

elif current_method == "ahp":
    st.warning(
        "**AHP** is not supported in this app. Create a **TOPSIS** or **VFT** scenario in Step 1 to view supported results."
    )
else:
    st.info(f"Results view for method `{current_method}` is not specialized in this build. Showing raw scores if available.")
    if not scores_df.empty:
        st.dataframe(scores_df, use_container_width=True)
