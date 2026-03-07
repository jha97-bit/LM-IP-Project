import streamlit as st
import pandas as pd
import plotly.express as px

def render_weighting_ui(model):
    st.header("Weighting (Swing Weights)")

    if not model.attributes:
        st.warning("Please add attributes in the Setup tab first.")
        return

    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("Adjust Swing Weights")
        st.write("Assign an importance value (0-100) to the swing of each attribute.")

        updated = False
        for attr in model.attributes:
            new_val = st.slider(
                f"{attr.name} ({attr.min_val} - {attr.max_val} {attr.unit})",
                min_value=0.0,
                max_value=100.0,
                value=attr.swing_weight,
                step=1.0,
                key=f"weight_slider_{attr.id}"
            )

            if new_val != attr.swing_weight:
                attr.swing_weight = new_val
                updated = True

        # Recalculate Weights
        total_swing = sum(a.swing_weight for a in model.attributes)
        if total_swing > 0:
            for a in model.attributes:
                a.weight = a.swing_weight / total_swing
        else:
            # Avoid division by zero, set equal weights
            for a in model.attributes:
                a.weight = 1.0 / len(model.attributes)

        if updated:
             st.rerun()

    with col2:
        st.subheader("Weight Distribution")

        # Pie Chart
        data = pd.DataFrame([{"Attribute": a.name, "Weight": a.weight} for a in model.attributes])

        if not data.empty:
            fig = px.pie(data, values="Weight", names="Attribute", title="Attribute Weights")
            st.plotly_chart(fig, width='stretch')

    st.subheader("Attribute Ranking")

    # Ranking Table
    ranking_data = []
    for attr in model.attributes:
        ranking_data.append({
            "Attribute": attr.name,
            "Swing Importance": attr.swing_weight,
            "Weight": attr.weight,
            "Weight (%)": f"{attr.weight * 100:.2f}%"
        })

    rank_df = pd.DataFrame(ranking_data)
    rank_df = rank_df.sort_values(by="Weight", ascending=False).reset_index(drop=True)
    rank_df["Rank"] = rank_df.index + 1

    # Add Importance Bin
    def get_bin(w):
        if w > 0.3: return "High"
        if w > 0.2: return "Medium"
        return "Low"

    rank_df["Importance Bin"] = rank_df["Weight"].apply(get_bin)

    # Reorder columns
    rank_df = rank_df[["Rank", "Attribute", "Swing Importance", "Weight (%)", "Importance Bin"]]

    # Color coding
    def highlight_bin(val):
        color = 'white'
        if val == 'High':
            color = '#d4edda' # Greenish
        elif val == 'Medium':
            color = '#fff3cd' # Yellowish
        elif val == 'Low':
            color = '#f8d7da' # Reddish
        return f'background-color: {color}; color: black'

    st.dataframe(
        rank_df.style.map(highlight_bin, subset=["Importance Bin"]),
        width='stretch',
        hide_index=True
    )
