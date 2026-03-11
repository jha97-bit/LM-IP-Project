import streamlit as st
import pandas as pd
import plotly.graph_objects as go

def render_comparison_ui(model):
    st.header("Alternative Comparison")

    if not model.attributes or not model.alternatives:
        st.warning("Please add attributes and alternatives in the Setup tab first.")
        return

    # Select Alternatives
    alt_names = [a.name for a in model.alternatives]
    selected_alts = st.multiselect("Select Alternatives to Compare", alt_names, default=alt_names[:2] if len(alt_names) >= 2 else alt_names)

    if not selected_alts:
        st.info("Select at least one alternative to see the comparison.")
        return

    # Data Preparation
    # We want Value Scores (0-1) for radar chart usually

    score_type = st.radio("Score Type for Radar Chart", ["Value Score (0-1)", "Weighted Score"], horizontal=True)

    radar_data = []

    for alt_name in selected_alts:
        alt = next((a for a in model.alternatives if a.name == alt_name), None)
        if alt:
            values = []
            for attr in model.attributes:
                raw = alt.get_score(attr.name)
                val = attr.get_value(raw)
                if score_type == "Weighted Score":
                    val = val * attr.weight
                values.append(val)

            # Close the loop for radar chart
            values.append(values[0])
            radar_data.append((alt_name, values))

    # Attributes for labels
    categories = [a.name for a in model.attributes]
    categories.append(categories[0]) # Close loop

    fig = go.Figure()

    for alt_name, values in radar_data:
        fig.add_trace(go.Scatterpolar(
            r=values,
            theta=categories,
            fill='toself',
            name=alt_name
        ))

    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 1] if score_type == "Value Score (0-1)" else None
            )
        ),
        showlegend=True,
        title=f"Comparison by {score_type}"
    )

    st.plotly_chart(fig, width='stretch')

    # Side-by-Side Table
    st.subheader("Detailed Comparison Table")

    # Rows: Attributes, Cols: Alternatives
    # We want to show Raw, Value, Weighted for each.

    comp_data = []
    for attr in model.attributes:
        row = {"Attribute": f"{attr.name} (Weight: {attr.weight:.2f})"}
        for alt_name in selected_alts:
            alt = next((a for a in model.alternatives if a.name == alt_name), None)
            if alt:
                raw = alt.get_score(attr.name)
                val = attr.get_value(raw)
                w_score = val * attr.weight
                # Format: "Raw (Weighted)"
                row[alt_name] = f"{raw:.2f}"
        comp_data.append(row)

    # Add Total Row
    total_row = {"Attribute": "Total Score"}
    for alt_name in selected_alts:
        alt = next((a for a in model.alternatives if a.name == alt_name), None)
        if alt:
            total = 0.0
            for attr in model.attributes:
                total += attr.get_value(alt.get_score(attr.name)) * attr.weight
            total_row[alt_name] = f"{total:.4f}"

    comp_data.append(total_row)

    st.dataframe(pd.DataFrame(comp_data), hide_index=True, width='stretch')
