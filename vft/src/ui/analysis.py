import streamlit as st
import pandas as pd
import plotly.express as px

def render_analysis_ui(model):
    st.header("Scoring & Analysis")

    if not model.attributes or not model.alternatives:
        st.warning("Please add attributes and alternatives in the Setup tab first.")
        return

    tab1, tab2, tab3 = st.tabs(["Scoring Matrix", "Analysis Dashboard", "Save to Database"])

    with tab1:
        st.subheader("Scoring Matrix (Raw Scores)")
        st.write("Enter raw scores for each alternative against each attribute.")

        # Prepare DataFrame
        # Rows: Alternatives
        # Columns: Attributes

        data = []
        for alt in model.alternatives:
            row = {"Alternative": alt.name, "ID": alt.id}
            for attr in model.attributes:
                row[attr.name] = alt.get_score(attr.name)
            data.append(row)

        if not data:
            df = pd.DataFrame(columns=["Alternative", "ID"] + [a.name for a in model.attributes])
        else:
            df = pd.DataFrame(data)

        # Configure columns
        column_config = {
            "ID": st.column_config.TextColumn(disabled=True),
            "Alternative": st.column_config.TextColumn(disabled=True)
        }
        for attr in model.attributes:
             column_config[attr.name] = st.column_config.NumberColumn(
                 label=f"{attr.name} ({attr.unit})",
                 required=True,
                 step=0.1
             )

        # Columns to display: Alternative, then all attributes
        column_order = ["Alternative"] + [attr.name for attr in model.attributes]

        edited_df = st.data_editor(
            df,
            key="scoring_matrix",
            column_order=column_order,
            column_config=column_config,
            hide_index=True,
            width='stretch'
        )

        # Update Scores
        # Iterate over edited_df and update model
        # We assume rows are aligned by ID. But safer to look up by ID.
        if not edited_df.equals(df):
             for _, row in edited_df.iterrows():
                 alt_id = row["ID"]
                 alt = next((a for a in model.alternatives if a.id == alt_id), None)
                 if alt:
                     for attr in model.attributes:
                         val = row.get(attr.name)
                         if val is not None:
                             alt.set_score(attr.name, float(val))
             # Rerun to refresh analysis? Not necessarily needed if user stays on tab.
             # But if they switch tab, model is updated.

    with tab2:
        st.subheader("Analysis Dashboard")

        # Calculate Scores
        results_df = model.calculate_scores()

        if results_df.empty:
            st.info("No results to display.")
        else:
            # Ranking Table
            st.markdown("### Ranking")
            rank_df = results_df[["Alternative", "Total Score"]].copy()
            rank_df = rank_df.sort_values(by="Total Score", ascending=False).reset_index(drop=True)
            rank_df["Rank"] = rank_df.index + 1
            rank_df = rank_df[["Rank", "Alternative", "Total Score"]]

            st.dataframe(rank_df, hide_index=True, width='stretch')

            # Stacked Bar Chart (Contribution)
            st.markdown("### Contribution Analysis")

            # Prepare data for plotting
            # calculate_scores returns columns like "Attr (Weighted)"

            plot_data = []
            for _, row in results_df.iterrows():
                alt_name = row["Alternative"]
                for attr in model.attributes:
                    col_name = f"{attr.name} (Weighted)"
                    if col_name in row:
                        plot_data.append({
                            "Alternative": alt_name,
                            "Attribute": attr.name,
                            "Weighted Score": row[col_name]
                        })

            if plot_data:
                plot_df = pd.DataFrame(plot_data)
                fig = px.bar(
                    plot_df,
                    x="Alternative",
                    y="Weighted Score",
                    color="Attribute",
                    title="Score Contribution by Attribute",
                    text_auto='.2f'
                )
                st.plotly_chart(fig, width='stretch')

            # Detailed Table
            with st.expander("Detailed Results Table"):
                st.dataframe(results_df, hide_index=True)

    with tab3:
        st.subheader("Persist Run to Database")
        st.write(
            "Save the current model state (attributes, alternatives, scores, "
            "utilities, and rankings) as a new VFT run in the database."
        )

        # --- DB connection check ---
        try:
            from persistence.engine import get_engine, ping_db
            from services import VftService

            db_ok = ping_db()
        except Exception:
            db_ok = False

        if not db_ok:
            st.error(
                "Database is not reachable. Ensure DATABASE_URL is set in your `.env` "
                "file and the PostgreSQL server is running."
            )
            return

        st.success("Database connection OK.")

        # --- user inputs ---
        executed_by = st.text_input("Your name / identifier", value="", key="vft_db_user")

        # --- validation ---
        has_scores = any(
            alt.get_score(attr.name) != 0.0
            for alt in model.alternatives
            for attr in model.attributes
        )
        weights_ok = any(attr.weight > 0 for attr in model.attributes)

        if not has_scores:
            st.warning("Enter raw scores in the Scoring Matrix tab before saving.")
        if not weights_ok:
            st.warning("Set attribute weights in the Weighting page before saving.")

        # --- save button ---
        if st.button("Save & Run to Database", type="primary", disabled=(not has_scores or not weights_ok)):
            try:
                engine = get_engine()
                service = VftService(engine)
                run_id = service.execute_vft_run(
                    model=model,
                    executed_by=executed_by.strip(),
                )
                st.session_state["last_vft_run_id"] = run_id
                st.success(f"VFT run saved successfully!  Run ID: `{run_id}`")
                st.info("Go to the **Run History** page to view saved runs and detailed results.")
            except Exception as e:
                st.error(f"Failed to save run: {e}")
