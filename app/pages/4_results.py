import bootstrap  # noqa: F401

import pandas as pd
import streamlit as st
from sqlalchemy import text
import plotly.express as px
import plotly.graph_objects as go

from persistence.engine import get_engine
from persistence.repositories.measurement_repo import MeasurementRepo
from persistence.repositories.preference_repo import PreferenceRepo
from persistence.repositories.run_repo import RunRepo
from persistence.repositories.result_repo import ResultRepo
from persistence.repositories.topsis_read_repo import TopsisReadRepo

st.title("Step 4: Results")

engine = get_engine()

# Repos
run_repo = RunRepo(engine)
result_repo = ResultRepo(engine)
topsis_read = TopsisReadRepo(engine)
meas_repo = MeasurementRepo(engine)
pref_repo = PreferenceRepo(engine)

# Navigation
nav_left, nav_right = st.columns(2)
with nav_left:
    if st.button("Back: Step 3 (Run Models)"):
        st.switch_page("pages/3_run_models.py")
with nav_right:
    if st.button("Next: Step 5 (History)"):
        st.switch_page("pages/5_history.py")

st.divider()

# =========================================================
# Decision -> Scenario -> Preference Set -> Run selectors
# =========================================================
st.subheader("Pick inputs to view results")

# ----------------------------
# Decisions (searchable)
# ----------------------------
with engine.begin() as conn:
    decisions = conn.execute(
        text("""
            SELECT decision_id::text AS decision_id, title, created_at
            FROM decisions
            ORDER BY created_at DESC
            LIMIT 500
        """)
    ).mappings().all()

decisions = [dict(d) for d in decisions]
if not decisions:
    st.warning("No decisions found. Create one in Step 1.")
    st.stop()

decision_ids = [d["decision_id"] for d in decisions]
decision_id_to_title = {d["decision_id"]: d.get("title") or d["decision_id"][:8] + "…" for d in decisions}

default_decision = st.session_state.get("decision_id") or decision_ids[0]
picked_decision = st.multiselect(
    "Decision",
    options=decision_ids,
    default=[default_decision] if default_decision in decision_ids else [decision_ids[0]],
    max_selections=1,
    format_func=lambda x: decision_id_to_title.get(x, x),
    key="pick_decision_step4",
)

decision_id = picked_decision[0] if picked_decision else decision_ids[0]
st.session_state["decision_id"] = decision_id

# ----------------------------
# Scenarios under decision (searchable)
# ----------------------------
with engine.begin() as conn:
    scenarios = conn.execute(
        text("""
            SELECT scenario_id::text AS scenario_id, name, created_at, created_by
            FROM scenarios
            WHERE decision_id = :did
            ORDER BY created_at DESC
            LIMIT 500
        """),
        {"did": decision_id},
    ).mappings().all()

scenarios = [dict(s) for s in scenarios]
if not scenarios:
    st.warning("No scenarios found for this decision. Create one in Step 1.")
    st.stop()

scenario_ids = [s["scenario_id"] for s in scenarios]
scenario_id_to_name = {s["scenario_id"]: (s.get("name") or s["scenario_id"][:8] + "…") for s in scenarios}

default_scenario = st.session_state.get("scenario_id")
if default_scenario not in scenario_ids:
    default_scenario = scenario_ids[0]

picked_scenario = st.multiselect(
    "Scenario",
    options=scenario_ids,
    default=[default_scenario],
    max_selections=1,
    format_func=lambda x: scenario_id_to_name.get(x, x),
    key=f"pick_scenario_step4_{decision_id}",
)

scenario_id = picked_scenario[0] if picked_scenario else scenario_ids[0]
st.session_state["scenario_id"] = scenario_id

# ----------------------------
# Preference sets under scenario (searchable)
# ----------------------------
with engine.begin() as conn:
    prefs = conn.execute(
        text("""
            SELECT preference_set_id::text AS preference_set_id, name, created_at
            FROM preference_sets
            WHERE scenario_id = :sid
            ORDER BY created_at DESC
        """),
        {"sid": scenario_id},
    ).mappings().all()

prefs = [dict(p) for p in prefs]
if not prefs:
    st.warning("No preference sets found for this scenario. Go to Step 2 and create one, then save weights.")
    st.stop()

pref_ids = [p["preference_set_id"] for p in prefs]
pref_id_to_name = {p["preference_set_id"]: p.get("name") or p["preference_set_id"][:8] + "…" for p in prefs}

default_pref = st.session_state.get("preference_set_id")
if default_pref not in pref_ids:
    default_pref = pref_ids[0]

picked_pref = st.multiselect(
    "Preference set",
    options=pref_ids,
    default=[default_pref],
    max_selections=1,
    format_func=lambda x: pref_id_to_name.get(x, x),
    key=f"pref_pick_step4_{scenario_id}",
)

pref_id = picked_pref[0] if picked_pref else pref_ids[0]
st.session_state["preference_set_id"] = pref_id

# ----------------------------
# Runs under scenario + preference set (TOPSIS only, searchable)
# ----------------------------
with engine.begin() as conn:
    runs = conn.execute(
        text("""
            SELECT run_id::text AS run_id, executed_at, executed_by
            FROM runs
            WHERE scenario_id = :sid
              AND preference_set_id = :pid
              AND method = 'topsis'
            ORDER BY executed_at DESC
            LIMIT 200
        """),
        {"sid": scenario_id, "pid": pref_id},
    ).mappings().all()

runs = [dict(r) for r in runs]
if not runs:
    st.warning("No TOPSIS runs found for this scenario + preference set. Go to Step 3 and run TOPSIS.")
    st.stop()

run_ids = [r["run_id"] for r in runs]

def _run_label(r: dict) -> str:
    by = (r.get("executed_by") or "").strip()
    by_part = f" by {by}" if by else ""
    return f"{r['executed_at']}{by_part} | {r['run_id'][:8]}…"

default_run = st.session_state.get("last_run_id")
if default_run not in run_ids:
    default_run = run_ids[0]

picked_run = st.multiselect(
    "TOPSIS run",
    options=run_ids,
    default=[default_run],
    max_selections=1,
    format_func=lambda x: _run_label(next(rr for rr in runs if rr["run_id"] == x)),
    key=f"run_pick_step4_{scenario_id}_{pref_id}",
)

run_id = picked_run[0] if picked_run else run_ids[0]
st.session_state["last_run_id"] = run_id

st.divider()

# =========================================================
# Run metadata
# =========================================================
with engine.begin() as conn:
    meta = conn.execute(
        text("""
            SELECT run_id::text AS run_id,
                   method,
                   engine_version,
                   executed_at,
                   executed_by,
                   preference_set_id::text AS preference_set_id
            FROM runs
            WHERE run_id = :rid
        """),
        {"rid": run_id},
    ).mappings().first()

if not meta:
    st.error("Selected run not found.")
    st.stop()

st.subheader("Run Summary")
st.write(
    {
        "decision": decision_id_to_title.get(decision_id, decision_id),
        "scenario": scenario_id_to_name.get(scenario_id, scenario_id),
        "preference_set": pref_id_to_name.get(pref_id, pref_id),
        "run_id": meta["run_id"],
        "method": meta["method"],
        "engine_version": meta.get("engine_version"),
        "executed_at": str(meta["executed_at"]),
        "executed_by": meta.get("executed_by"),
    }
)

st.divider()

# =========================================================
# Inputs used for results (Matrix + Weight row combined, right aligned)
# =========================================================
st.subheader("Inputs used for results")

matrix_df = meas_repo.load_matrix_ui(scenario_id)
weights_map = pref_repo.load_weights_by_criterion_name(pref_id)

if matrix_df is None or matrix_df.empty:
    st.info("No performance matrix found for this scenario yet. Fill Step 2 and save Matrix + Weights.")
    st.stop()

crit_cols = list(matrix_df.columns)
weights_row = {c: float(weights_map.get(c, 0.0)) for c in crit_cols}

weights_df = pd.DataFrame([weights_row], index=["Weight"])
combined_df = pd.concat([weights_df, matrix_df], axis=0)

def _fmt(x):
    if pd.isna(x):
        return ""
    try:
        return f"{float(x):.4f}"
    except Exception:
        return str(x)

combined_disp = combined_df.copy()
for c in combined_disp.columns:
    combined_disp[c] = combined_disp[c].map(_fmt)

cols = ["Alternative / Row"] + list(combined_disp.columns)
rows = []
for idx, row in combined_disp.iterrows():
    rows.append([str(idx)] + [row[c] for c in combined_disp.columns])

table_head = "".join([f"<th>{c}</th>" for c in cols])
table_body = ""
for r in rows:
    tds = [f"<td class='idx'>{r[0]}</td>"] + [f"<td>{v}</td>" for v in r[1:]]
    table_body += f"<tr>{''.join(tds)}</tr>"

table_html = f"""
<div class="mcda-panel">
  <div class="mcda-wrap">
    <table class="mcda-table">
      <thead><tr>{table_head}</tr></thead>
      <tbody>{table_body}</tbody>
    </table>
  </div>
</div>
"""

st.markdown(
    """
    <style>
      .mcda-panel { display: flex; justify-content: flex-end; width: 100%; }
      .mcda-wrap {
        width: 100%;
        max-width: 1200px;
        overflow-x: auto;
        border: 1px solid rgba(0,0,0,0.12);
        border-radius: 12px;
        background: rgba(255,255,255,0.02);
      }
      table.mcda-table {
        border-collapse: separate;
        border-spacing: 0;
        width: 100%;
        min-width: 900px;
        font-size: 14px;
      }
      .mcda-table thead th {
        position: sticky;
        top: 0;
        background: rgba(250,250,250,0.95);
        z-index: 2;
        text-align: right;
        padding: 10px 12px;
        border-bottom: 1px solid rgba(0,0,0,0.12);
        font-weight: 600;
        white-space: nowrap;
      }
      .mcda-table thead th:first-child { text-align: left; }
      .mcda-table tbody td {
        padding: 10px 12px;
        border-bottom: 1px solid rgba(0,0,0,0.08);
        text-align: right;
        white-space: nowrap;
      }
      .mcda-table tbody td.idx { text-align: left; font-weight: 600; }
      .mcda-table tbody tr:nth-child(odd) td { background: rgba(0,0,0,0.015); }
      .mcda-table tbody tr:first-child td {
        background: rgba(255, 235, 59, 0.12);
        font-weight: 700;
      }
    </style>
    """,
    unsafe_allow_html=True,
)
st.markdown(table_html, unsafe_allow_html=True)

st.download_button(
    "Download Matrix + Weights CSV",
    data=combined_df.to_csv().encode("utf-8"),
    file_name=f"matrix_with_weights_{run_id}.csv",
    mime="text/csv",
)

st.divider()

# =========================================================
# Load TOPSIS details and show tabs (same as before)
# =========================================================
scores = result_repo.get_scores_with_names(run_id)
scores_df = pd.DataFrame(scores)

dist_df = topsis_read.get_distances(run_id)
ideals_df = topsis_read.get_ideals(run_id)
norm_df = topsis_read.get_matrix(run_id, "normalized")
w_df = topsis_read.get_matrix(run_id, "weighted")

tab_rank, tab_dist, tab_ideals, tab_norm, tab_weighted = st.tabs(
    ["Ranking", "Distances", "Ideals (PIS/NIS)", "Normalized Matrix", "Weighted Matrix"]
)

with tab_rank:
    st.subheader("Ranking")
    st.dataframe(scores_df, width="stretch")

    st.download_button(
        "Download Ranking CSV",
        data=scores_df.to_csv(index=False).encode("utf-8"),
        file_name=f"ranking_{run_id}.csv",
        mime="text/csv",
    )

    if not scores_df.empty:
        fig_scores = px.bar(
            scores_df.sort_values("rank", ascending=True),
            x="alternative_name",
            y="score",
            hover_data=["rank"],
            title="TOPSIS Score (C*) by Alternative",
        )
        st.plotly_chart(fig_scores, use_container_width=True)

with tab_dist:
    st.subheader("Separation Measures")
    st.dataframe(dist_df, width="stretch")

    st.download_button(
        "Download Distances CSV",
        data=dist_df.to_csv(index=False).encode("utf-8"),
        file_name=f"topsis_distances_{run_id}.csv",
        mime="text/csv",
    )

    if not dist_df.empty:
        fig_scatter = px.scatter(
            dist_df,
            x="s_pos",
            y="s_neg",
            text="alternative",
            hover_data=["c_star"],
            title="S+ vs S- (better is low S+, high S-)",
        )
        fig_scatter.update_traces(textposition="top center")
        st.plotly_chart(fig_scatter, use_container_width=True)

with tab_ideals:
    st.subheader("Ideals Table (PIS/NIS)")
    st.dataframe(ideals_df, width="stretch")

    st.download_button(
        "Download Ideals CSV",
        data=ideals_df.to_csv(index=False).encode("utf-8"),
        file_name=f"topsis_ideals_{run_id}.csv",
        mime="text/csv",
    )

    st.subheader("PIS/NIS Valve View by Criterion")

    if w_df.empty or ideals_df.empty:
        st.info("Missing weighted matrix or ideals for this run.")
    else:
        w_df_plot = w_df.copy()
        w_df_plot.index.name = "alternative"
        w_long = w_df_plot.reset_index().melt(
            id_vars=["alternative"],
            var_name="criterion",
            value_name="weighted_value"
        )

        ideals_map = ideals_df.set_index("criterion")[["pos_ideal", "neg_ideal"]].to_dict(orient="index")

        crit_list = list(w_df_plot.columns)
        for c in crit_list:
            w_c = float(weights_row.get(c, 0.0))
            pos = float(ideals_map.get(c, {}).get("pos_ideal", 0.0))
            neg = float(ideals_map.get(c, {}).get("neg_ideal", 0.0))

            with st.expander(f"{c} | weight={w_c:.4f}", expanded=False):
                df_c = w_long[w_long["criterion"] == c].copy()
                df_c = df_c.sort_values("weighted_value", ascending=False)

                st.dataframe(df_c[["alternative", "weighted_value"]], width="stretch")

                fig = go.Figure()
                fig.add_trace(
                    go.Scatter(
                        x=df_c["weighted_value"],
                        y=df_c["alternative"],
                        mode="markers+text",
                        text=[f"{v:.4f}" for v in df_c["weighted_value"]],
                        textposition="middle right",
                        name="Alternative (weighted)",
                        hovertemplate="Alternative=%{y}<br>Weighted value=%{x:.6f}<extra></extra>",
                    )
                )

                fig.add_vline(x=pos, line_width=2, line_dash="solid", annotation_text="PIS", annotation_position="top")
                fig.add_vline(x=neg, line_width=2, line_dash="dash", annotation_text="NIS", annotation_position="bottom")

                xmin = min(df_c["weighted_value"].min(), pos, neg)
                xmax = max(df_c["weighted_value"].max(), pos, neg)
                pad = (xmax - xmin) * 0.1 if xmax > xmin else 0.1
                fig.update_xaxes(range=[xmin - pad, xmax + pad])

                fig.update_layout(
                    title=f"Valve View: {c} (weighted values) with PIS/NIS",
                    xaxis_title="Weighted value",
                    yaxis_title="Alternative",
                    height=420,
                    margin=dict(l=10, r=10, t=60, b=10),
                )

                st.plotly_chart(fig, use_container_width=True)

with tab_norm:
    st.subheader("Normalized Matrix")
    if norm_df.empty:
        st.info("No normalized matrix found for this run.")
    else:
        st.dataframe(norm_df, width="stretch")
        st.download_button(
            "Download Normalized Matrix CSV",
            data=norm_df.to_csv().encode("utf-8"),
            file_name=f"topsis_normalized_matrix_{run_id}.csv",
            mime="text/csv",
        )

with tab_weighted:
    st.subheader("Weighted Matrix")
    if w_df.empty:
        st.info("No weighted matrix found for this run.")
    else:
        st.dataframe(w_df, width="stretch")
        st.download_button(
            "Download Weighted Matrix CSV",
            data=w_df.to_csv().encode("utf-8"),
            file_name=f"topsis_weighted_matrix_{run_id}.csv",
            mime="text/csv",
        )

        heat_df = w_df.copy()
        fig_heat = px.imshow(
            heat_df.values,
            x=list(heat_df.columns),
            y=list(heat_df.index),
            aspect="auto",
            title="Weighted Matrix Heatmap",
        )
        st.plotly_chart(fig_heat, use_container_width=True)
