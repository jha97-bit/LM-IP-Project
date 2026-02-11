import bootstrap

import pandas as pd
import streamlit as st
from sqlalchemy import text
import plotly.express as px
import plotly.graph_objects as go

from persistence.engine import get_engine
from persistence.repositories.result_repo import ResultRepo
from persistence.repositories.run_repo import RunRepo
from persistence.repositories.topsis_read_repo import TopsisReadRepo

st.title("Step 4: Results")

engine = get_engine()
scenario_id = st.session_state.get("scenario_id")
if not scenario_id:
    st.info("Go to Step 1 and select a Scenario first.")
    st.stop()

# Navigation
nav_left, nav_right = st.columns(2)
with nav_left:
    if st.button("Back: Step 3 (Run Models)"):
        st.switch_page("pages/3_run_models.py")
with nav_right:
    if st.button("Next: Step 5 (History)"):
        st.switch_page("pages/5_history.py")

st.divider()

run_repo = RunRepo(engine)
result_repo = ResultRepo(engine)
topsis_read = TopsisReadRepo(engine)

runs = run_repo.list_runs(scenario_id, limit=50)
topsis_runs = [r for r in runs if r["method"] == "topsis"]

if not topsis_runs:
    st.warning("No TOPSIS runs yet. Go to Step 3 and run TOPSIS first.")
    st.stop()

default_run = st.session_state.get("last_run_id")
if default_run not in [r["run_id"] for r in topsis_runs]:
    default_run = topsis_runs[0]["run_id"]

run_id = st.selectbox(
    "Select a TOPSIS run",
    options=[r["run_id"] for r in topsis_runs],
    index=[r["run_id"] for r in topsis_runs].index(default_run),
    format_func=lambda x: next(
        f"{rr['executed_at']} | {rr.get('executed_by','')} | pref={rr['preference_set_id'][:8]}…"
        for rr in topsis_runs if rr["run_id"] == x
    ),
)

st.session_state["last_run_id"] = run_id

# Run metadata
with engine.begin() as conn:
    meta = conn.execute(
        text("""
            SELECT run_id::text AS run_id, method, engine_version, executed_at, executed_by,
                   preference_set_id::text AS preference_set_id
            FROM runs
            WHERE run_id = :rid
        """),
        {"rid": run_id},
    ).mappings().first()

st.subheader("Run Summary")
st.write(
    {
        "run_id": meta["run_id"],
        "method": meta["method"],
        "engine_version": meta["engine_version"],
        "executed_at": str(meta["executed_at"]),
        "executed_by": meta.get("executed_by"),
        "preference_set_id": meta["preference_set_id"],
    }
)

st.divider()

# Ranking table
st.subheader("Ranking")
scores = result_repo.get_scores_with_names(run_id)
scores_df = pd.DataFrame(scores)
st.dataframe(scores_df, use_container_width=True)

st.download_button(
    "Download Ranking CSV",
    data=scores_df.to_csv(index=False).encode("utf-8"),
    file_name=f"ranking_{run_id}.csv",
    mime="text/csv",
)

st.divider()

# TOPSIS details
st.subheader("TOPSIS Details")

dist_df = topsis_read.get_distances(run_id)
ideals_df = topsis_read.get_ideals(run_id)
norm_df = topsis_read.get_matrix(run_id, "normalized")
w_df = topsis_read.get_matrix(run_id, "weighted")

tab1, tab2, tab3, tab4 = st.tabs(["Distances", "Ideals (PIS/NIS)", "Normalized Matrix", "Weighted Matrix"])

with tab1:
    st.dataframe(dist_df, use_container_width=True)
    st.download_button(
        "Download Distances CSV",
        data=dist_df.to_csv(index=False).encode("utf-8"),
        file_name=f"topsis_distances_{run_id}.csv",
        mime="text/csv",
    )

with tab2:
    st.dataframe(ideals_df, use_container_width=True)
    st.download_button(
        "Download Ideals CSV",
        data=ideals_df.to_csv(index=False).encode("utf-8"),
        file_name=f"topsis_ideals_{run_id}.csv",
        mime="text/csv",
    )

with tab3:
    if norm_df.empty:
        st.info("No normalized matrix found for this run.")
    else:
        st.dataframe(norm_df, use_container_width=True)
        st.download_button(
            "Download Normalized Matrix CSV",
            data=norm_df.to_csv().encode("utf-8"),
            file_name=f"topsis_normalized_matrix_{run_id}.csv",
            mime="text/csv",
        )

with tab4:
    if w_df.empty:
        st.info("No weighted matrix found for this run.")
    else:
        st.dataframe(w_df, use_container_width=True)
        st.download_button(
            "Download Weighted Matrix CSV",
            data=w_df.to_csv().encode("utf-8"),
            file_name=f"topsis_weighted_matrix_{run_id}.csv",
            mime="text/csv",
        )

st.subheader("Charts")

if not scores_df.empty:
    fig_scores = px.bar(
        scores_df.sort_values("rank", ascending=True),
        x="alternative_name",
        y="score",
        hover_data=["rank"],
        title="TOPSIS Score (C*) by Alternative",
    )
    st.plotly_chart(fig_scores, use_container_width=True)

if not dist_df.empty:
    fig_scatter = px.scatter(
        dist_df,
        x="s_pos",
        y="s_neg",
        text="alternative",
        hover_data=["c_star"],
        title="Separation Measures: S+ vs S-",
    )
    fig_scatter.update_traces(textposition="top center")
    st.plotly_chart(fig_scatter, use_container_width=True)

if not w_df.empty:
    heat_df = w_df.copy()
    fig_heat = px.imshow(
        heat_df.values,
        x=list(heat_df.columns),
        y=list(heat_df.index),
        aspect="auto",
        title="Weighted Matrix Heatmap",
    )
    st.plotly_chart(fig_heat, use_container_width=True)

if not ideals_df.empty:
    ideals_long = ideals_df.melt(id_vars=["criterion"], value_vars=["pos_ideal", "neg_ideal"],
                                 var_name="ideal_type", value_name="value")
    fig_ideals = px.bar(
        ideals_long,
        x="criterion",
        y="value",
        color="ideal_type",
        barmode="group",
        title="PIS vs NIS by Criterion",
    )
    st.plotly_chart(fig_ideals, use_container_width=True)
