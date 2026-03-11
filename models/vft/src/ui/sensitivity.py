import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

def render_sensitivity_ui(model):
    st.header("Sensitivity Analysis")

    if not model.attributes or not model.alternatives:
        st.warning("Please add attributes and alternatives in the Setup tab first.")
        return

    st.write("Analyze how changes in attribute weights and scores affect the overall score and ranking of alternatives.")

    tab1, tab2, tab3 = st.tabs(["Weight Sensitivity", "Objective Score Sensitivity", "Robustness Analysis"])

    # Pre-calculate value scores for all alternatives and attributes
    alt_value_scores = {}
    base_total_scores = {}
    for alt in model.alternatives:
        alt_value_scores[alt.name] = {}
        total = 0.0
        for attr in model.attributes:
            raw = alt.get_score(attr.name)
            val = attr.get_value(raw)
            alt_value_scores[alt.name][attr.name] = val
            total += val * attr.weight
        base_total_scores[alt.name] = total

    # --- TAB 1: Weight Sensitivity ---
    with tab1:
        st.subheader("Weight Sensitivity")
        st.write("Analyzes how changing the importance (weight) of a specific objective alters which alternative is ranked best.")

        attr_names = [a.name for a in model.attributes]
        selected_attr_name_w = st.selectbox("Select Attribute to Vary", attr_names, key="weight_sens_attr")
        selected_attr_w = next((a for a in model.attributes if a.name == selected_attr_name_w), None)

        if selected_attr_w:
            weight_range = np.linspace(0.0, 1.0, 50)
            other_attrs = [a for a in model.attributes if a.name != selected_attr_w.name]
            base_other_weights = {a.name: a.weight for a in other_attrs}
            sum_other_weights = sum(base_other_weights.values())

            plot_data_w = []
            for w in weight_range:
                for alt in model.alternatives:
                    total_score = alt_value_scores[alt.name][selected_attr_w.name] * w

                    if sum_other_weights > 0:
                        remaining_weight = 1.0 - w
                        for other_attr in other_attrs:
                            proportional_weight = base_other_weights[other_attr.name] / sum_other_weights * remaining_weight
                            total_score += alt_value_scores[alt.name][other_attr.name] * proportional_weight
                    else:
                        if other_attrs:
                            remaining_weight = 1.0 - w
                            equal_weight = remaining_weight / len(other_attrs)
                            for other_attr in other_attrs:
                                total_score += alt_value_scores[alt.name][other_attr.name] * equal_weight

                    plot_data_w.append({
                        "Weight of Selected Attribute": w,
                        "Alternative": alt.name,
                        "Total Score": total_score
                    })

            df_w = pd.DataFrame(plot_data_w)
            fig_w = px.line(
                df_w,
                x="Weight of Selected Attribute",
                y="Total Score",
                color="Alternative",
                title=f"Weight Sensitivity Analysis for {selected_attr_w.name}",
                labels={"Weight of Selected Attribute": f"Weight of {selected_attr_w.name}", "Total Score": "Overall Score"}
            )
            current_weight = selected_attr_w.weight
            fig_w.add_vline(x=current_weight, line_dash="dash", line_color="gray", annotation_text="Current Weight", annotation_position="top right")
            fig_w.update_layout(yaxis_range=[-0.05, 1.05], xaxis_range=[-0.05, 1.05])
            st.plotly_chart(fig_w, width='stretch')

    # --- TAB 2: Objective Score Sensitivity ---
    with tab2:
        st.subheader("Objective Score Sensitivity")
        st.write("Tests how uncertainty in an alternative’s performance score for a particular objective affects the final outcome.")

        col1, col2 = st.columns(2)
        with col1:
            alt_names = [a.name for a in model.alternatives]
            selected_alt_name_s = st.selectbox("Select Alternative", alt_names, key="score_sens_alt")
            selected_alt_s = next((a for a in model.alternatives if a.name == selected_alt_name_s), None)

        with col2:
            selected_attr_name_s = st.selectbox("Select Attribute to Vary", attr_names, key="score_sens_attr")
            selected_attr_s = next((a for a in model.attributes if a.name == selected_attr_name_s), None)

        if selected_alt_s and selected_attr_s:
            # Vary score from min to max
            score_range = np.linspace(selected_attr_s.min_val, selected_attr_s.max_val, 50)

            # Calculate base scores for OTHER alternatives to plot them as flat lines
            other_alts = [a for a in model.alternatives if a.name != selected_alt_s.name]

            plot_data_s = []

            for score in score_range:
                # Calculate new value for the selected attribute and alternative
                new_val = selected_attr_s.get_value(score)

                # Calculate total score for selected alternative
                new_total = 0.0
                for attr in model.attributes:
                    if attr.name == selected_attr_s.name:
                        new_total += new_val * attr.weight
                    else:
                        new_total += alt_value_scores[selected_alt_s.name][attr.name] * attr.weight

                plot_data_s.append({
                    "Raw Score": score,
                    "Alternative": selected_alt_s.name,
                    "Total Score": new_total
                })

                # Add constant lines for other alternatives for comparison
                for other_alt in other_alts:
                    plot_data_s.append({
                        "Raw Score": score,
                        "Alternative": other_alt.name,
                        "Total Score": base_total_scores[other_alt.name]
                    })

            df_s = pd.DataFrame(plot_data_s)
            fig_s = px.line(
                df_s,
                x="Raw Score",
                y="Total Score",
                color="Alternative",
                title=f"Score Sensitivity for {selected_alt_s.name} on {selected_attr_s.name}",
                labels={"Raw Score": f"Raw Score ({selected_attr_s.unit})", "Total Score": "Overall Score"}
            )

            current_raw_score = selected_alt_s.get_score(selected_attr_s.name)
            fig_s.add_vline(x=current_raw_score, line_dash="dash", line_color="gray", annotation_text="Current Score", annotation_position="top right")
            fig_s.update_layout(yaxis_range=[-0.05, 1.05])
            st.plotly_chart(fig_s, width='stretch')

    # --- TAB 3: Robustness Analysis ---
    with tab3:
        st.subheader("Robustness Analysis")
        st.write("Identifies which alternative remains superior even when input assumptions are varied, using a Tornado chart to show which variables have the greatest impact.")

        # Determine the top alternative by default
        ranked_alts = sorted(base_total_scores.items(), key=lambda item: item[1], reverse=True)
        top_alt_name = ranked_alts[0][0] if ranked_alts else None

        selected_alt_name_r = st.selectbox("Select Alternative for Tornado Chart", alt_names, index=alt_names.index(top_alt_name) if top_alt_name in alt_names else 0, key="robust_sens_alt")
        selected_alt_r = next((a for a in model.alternatives if a.name == selected_alt_name_r), None)

        if selected_alt_r:
            tornado_data = []
            base_score = base_total_scores[selected_alt_r.name]

            for attr in model.attributes:
                other_attrs = [a for a in model.attributes if a.name != attr.name]
                base_other_weights = {a.name: a.weight for a in other_attrs}
                sum_other_weights = sum(base_other_weights.values())

                # Scenario 1: Weight = 0
                w_0_score = 0.0
                if sum_other_weights > 0:
                    for other_attr in other_attrs:
                        proportional_weight = base_other_weights[other_attr.name] / sum_other_weights * 1.0
                        w_0_score += alt_value_scores[selected_alt_r.name][other_attr.name] * proportional_weight
                else:
                    if other_attrs:
                        equal_weight = 1.0 / len(other_attrs)
                        for other_attr in other_attrs:
                            w_0_score += alt_value_scores[selected_alt_r.name][other_attr.name] * equal_weight

                # Scenario 2: Weight = 1
                w_1_score = alt_value_scores[selected_alt_r.name][attr.name] * 1.0

                # Calculate the swing (impact)
                min_impact = min(w_0_score, w_1_score)
                max_impact = max(w_0_score, w_1_score)
                spread = max_impact - min_impact

                # We need to know which is which for the chart
                w_0_is_min = w_0_score == min_impact

                tornado_data.append({
                    "Attribute": attr.name,
                    "Base Score": base_score,
                    "Weight=0 Score": w_0_score,
                    "Weight=1 Score": w_1_score,
                    "Min Score": min_impact,
                    "Max Score": max_impact,
                    "Spread": spread
                })

            df_t = pd.DataFrame(tornado_data)

            if not df_t.empty:
                # Sort by spread for Tornado effect
                df_t = df_t.sort_values(by="Spread", ascending=True) # Ascending because Plotly bar charts draw from bottom up

                fig_t = go.Figure()

                # Add base line
                fig_t.add_shape(
                    type="line",
                    x0=base_score, y0=-0.5, x1=base_score, y1=len(df_t)-0.5,
                    line=dict(color="black", width=2, dash="dash"),
                )

                # Adding two traces to represent the "left" and "right" sides of the base score.
                fig_t.add_trace(go.Bar(
                    y=df_t["Attribute"],
                    x=df_t["Max Score"] - df_t["Min Score"],
                    base=df_t["Min Score"],
                    orientation='h',
                    marker_color='lightblue',
                    name="Score Range"
                ))

                fig_t.update_layout(
                    title=f"Tornado Chart: Impact of Attribute Weights on {selected_alt_r.name}",
                    xaxis_title="Overall Score",
                    yaxis_title="Attribute",
                    barmode='overlay',
                    xaxis_range=[0, 1.1],
                    showlegend=False
                )

                # Add annotations for Weight 0 and Weight 1
                for i, row in df_t.iterrows():
                    fig_t.add_annotation(
                        x=row["Weight=0 Score"],
                        y=row["Attribute"],
                        text="W=0",
                        showarrow=False,
                        xanchor="right" if row["Weight=0 Score"] < row["Weight=1 Score"] else "left",
                        font=dict(size=10, color="red")
                    )
                    fig_t.add_annotation(
                        x=row["Weight=1 Score"],
                        y=row["Attribute"],
                        text="W=1",
                        showarrow=False,
                        xanchor="left" if row["Weight=1 Score"] > row["Weight=0 Score"] else "right",
                        font=dict(size=10, color="green")
                    )

                st.plotly_chart(fig_t, width='stretch')
            else:
                st.info("No data to display for Robustness Analysis.")
