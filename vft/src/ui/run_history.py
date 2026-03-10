"""
VFT Run History UI — browse, inspect, and export persisted VFT runs.
Uses VftRunRepo + VftReadRepo (mirrors the TOPSIS results / history pages).
"""
import json

import streamlit as st
import pandas as pd
import plotly.express as px

from persistence.engine import get_engine, ping_db
from persistence.repositories import VftRunRepo, VftReadRepo


def render_run_history_ui():
    """Display run history and results from database."""
    st.header("Run History & Results")

    # --- DB connection ---
    if not ping_db():
        st.error("Database connection failed. Check DATABASE_URL.")
        return

    engine = get_engine()
    run_repo = VftRunRepo(engine)
    read_repo = VftReadRepo(engine)

    # --- list all runs ---
    runs = run_repo.list_runs(limit=100)

    if not runs:
        st.info(
            "No VFT runs found in database. Go to **Scoring & Analysis → Save to Database** "
            "to create a run."
        )
        return

    runs_df = pd.DataFrame(runs)

    st.subheader("VFT Runs")
    st.dataframe(
        runs_df[["executed_at", "executed_by", "engine_version", "run_id"]],
        hide_index=True,
        use_container_width=True,
        column_config={
            "executed_at": st.column_config.DatetimeColumn("Executed At", format="YYYY-MM-DD HH:mm:ss"),
            "executed_by": st.column_config.TextColumn("Executed By", width="small"),
            "engine_version": st.column_config.TextColumn("Engine Version", width="small"),
            "run_id": st.column_config.TextColumn("Run ID", width="medium"),
        },
    )

    # --- select a run ---
    st.markdown("---")
    st.subheader("View Run Details")

    selected_idx = st.selectbox(
        "Select a run to view results:",
        range(len(runs_df)),
        format_func=lambda i: (
            f"{runs_df.iloc[i]['executed_at'].strftime('%Y-%m-%d %H:%M:%S')} "
            f"– {runs_df.iloc[i]['executed_by'] or '(no user)'} "
            f"– {runs_df.iloc[i]['run_id'][:12]}…"
        ),
        key="vft_run_selector",
    )

    run_id = runs_df.iloc[selected_idx]["run_id"]

    # --- tabs for run details ---
    tab_summary, tab_criteria, tab_raw, tab_utility, tab_weighted, tab_results = st.tabs(
        ["Summary", "Criteria", "Raw Scores", "Utilities", "Weighted Utilities", "Results"]
    )

    # ===== Summary =====
    with tab_summary:
        st.markdown("### Run Information")
        meta = runs_df.iloc[selected_idx]
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**Run ID**: `{run_id}`")
            st.write(f"**Executed At**: {meta['executed_at']}")
        with col2:
            st.write(f"**Executed By**: {meta.get('executed_by', '')}")
            st.write(f"**Engine Version**: {meta.get('engine_version', '')}")

        config = read_repo.get_run_config(run_id)
        if config:
            st.write(f"**Scaling Type**: {config.get('scaling_type', 'N/A')}")
            st.write(f"**Output Range**: {config.get('output_min', 0.0)} – {config.get('output_max', 1.0)}")

    # ===== Criteria =====
    with tab_criteria:
        st.markdown("### Criteria (Attributes)")
        criteria_df = read_repo.get_criteria(run_id)
        if criteria_df.empty:
            st.info("No criteria found for this run.")
        else:
            st.dataframe(
                criteria_df,
                hide_index=True,
                use_container_width=True,
                column_config={
                    "criteria_id": st.column_config.TextColumn("Criteria ID", width="medium"),
                    "name": st.column_config.TextColumn("Name", width="small"),
                    "weight": st.column_config.NumberColumn("Weight", format="%.3f"),
                    "swing_weight": st.column_config.NumberColumn("Swing Weight", format="%.1f"),
                    "min_val": st.column_config.NumberColumn("Min", format="%.2f"),
                    "max_val": st.column_config.NumberColumn("Max", format="%.2f"),
                    "scaling_direction": st.column_config.TextColumn("Direction", width="small"),
                    "scaling_type": st.column_config.TextColumn("Type", width="small"),
                },
            )

    # ===== Raw Scores =====
    with tab_raw:
        st.markdown("### Raw Scores (Input Matrix)")
        raw_matrix = read_repo.get_raw_scores_matrix(run_id)
        if raw_matrix.empty:
            st.info("No raw scores found for this run.")
        else:
            st.dataframe(raw_matrix, use_container_width=True)
            st.download_button(
                "Download Raw Scores CSV",
                data=raw_matrix.to_csv().encode("utf-8"),
                file_name=f"vft_raw_scores_{run_id[:8]}.csv",
                mime="text/csv",
            )

    # ===== Utility Values =====
    with tab_utility:
        st.markdown("### Value Function Utilities (0–1)")
        utility_matrix = read_repo.get_utility_matrix(run_id)
        if utility_matrix.empty:
            st.info("No utility data found for this run.")
        else:
            st.dataframe(utility_matrix, use_container_width=True)

            # Heatmap
            fig_heat = px.imshow(
                utility_matrix.values,
                x=list(utility_matrix.columns),
                y=list(utility_matrix.index),
                aspect="auto",
                title="Utility Matrix Heatmap",
                color_continuous_scale="Viridis",
            )
            st.plotly_chart(fig_heat, use_container_width=True)

            st.download_button(
                "Download Utility Matrix CSV",
                data=utility_matrix.to_csv().encode("utf-8"),
                file_name=f"vft_utility_matrix_{run_id[:8]}.csv",
                mime="text/csv",
            )

    # ===== Weighted Utilities =====
    with tab_weighted:
        st.markdown("### Weighted Utilities (utility × weight)")
        weighted_matrix = read_repo.get_weighted_utility_matrix(run_id)
        if weighted_matrix.empty:
            st.info("No weighted utility data found for this run.")
        else:
            st.dataframe(weighted_matrix, use_container_width=True)

            fig_heat_w = px.imshow(
                weighted_matrix.values,
                x=list(weighted_matrix.columns),
                y=list(weighted_matrix.index),
                aspect="auto",
                title="Weighted Utility Heatmap",
                color_continuous_scale="Viridis",
            )
            st.plotly_chart(fig_heat_w, use_container_width=True)

            st.download_button(
                "Download Weighted Utility Matrix CSV",
                data=weighted_matrix.to_csv().encode("utf-8"),
                file_name=f"vft_weighted_utilities_{run_id[:8]}.csv",
                mime="text/csv",
            )

    # ===== Results =====
    with tab_results:
        st.markdown("### Results & Rankings")
        scores_df = read_repo.get_result_scores(run_id)
        if scores_df.empty:
            st.info("No result scores found for this run.")
        else:
            st.dataframe(
                scores_df,
                hide_index=True,
                use_container_width=True,
                column_config={
                    "rank": st.column_config.NumberColumn("Rank", width="small"),
                    "alternative": st.column_config.TextColumn("Alternative"),
                    "total_score": st.column_config.NumberColumn("Total Score", format="%.4f"),
                },
            )

            # Bar chart
            fig_bar = px.bar(
                scores_df.sort_values("rank"),
                x="alternative",
                y="total_score",
                hover_data=["rank"],
                title="VFT Total Score by Alternative",
            )
            st.plotly_chart(fig_bar, use_container_width=True)

            # Contribution chart (weighted utilities stacked)
            weighted_flat = read_repo.get_weighted_utilities(run_id)
            if not weighted_flat.empty:
                fig_contrib = px.bar(
                    weighted_flat,
                    x="alternative",
                    y="weighted_utility",
                    color="criterion",
                    title="Score Contribution by Attribute",
                    text_auto=".3f",
                )
                st.plotly_chart(fig_contrib, use_container_width=True)

            st.download_button(
                "Download Results CSV",
                data=scores_df.to_csv(index=False).encode("utf-8"),
                file_name=f"vft_results_{run_id[:8]}.csv",
                mime="text/csv",
            )

    # --- export full run as JSON ---
    st.markdown("---")
    st.subheader("Export Run")

    criteria_df = read_repo.get_criteria(run_id)
    alts_df = read_repo.get_alternatives(run_id)
    scores_df = read_repo.get_result_scores(run_id)
    config_data = read_repo.get_run_config(run_id)

    export_data = {
        "run_id": run_id,
        "executed_at": str(runs_df.iloc[selected_idx]["executed_at"]),
        "executed_by": runs_df.iloc[selected_idx].get("executed_by", ""),
        "engine_version": runs_df.iloc[selected_idx].get("engine_version", ""),
        "config": config_data or {},
        "criteria": criteria_df.to_dict(orient="records") if not criteria_df.empty else [],
        "alternatives": alts_df.to_dict(orient="records") if not alts_df.empty else [],
        "results": scores_df.to_dict(orient="records") if not scores_df.empty else [],
    }

    json_str = json.dumps(export_data, indent=2, default=str)
    st.download_button(
        label="Download Run as JSON",
        data=json_str,
        file_name=f"vft_run_{run_id[:8]}.json",
        mime="application/json",
    )
