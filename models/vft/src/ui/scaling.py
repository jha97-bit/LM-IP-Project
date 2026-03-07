import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

def render_scaling_ui(model):
    st.header("Value Functions (Scaling)")

    if not model.attributes:
        st.warning("Please add attributes in the Setup tab first.")
        return

    # Select Attribute
    attr_names = [a.name for a in model.attributes]
    selected_attr_name = st.selectbox("Select Attribute to Configure", attr_names)

    selected_attr = next((a for a in model.attributes if a.name == selected_attr_name), None)

    if selected_attr:
        col1, col2 = st.columns([1, 2])

        with col1:
            st.subheader("Configuration")

            # Scaling Type
            scaling_type = st.selectbox(
                "Scaling Type",
                ["Linear", "Custom"],
                index=0 if selected_attr.scaling_type == "Linear" else 1
            )

            if scaling_type != selected_attr.scaling_type:
                selected_attr.scaling_type = scaling_type
                st.rerun()

            if scaling_type == "Linear":
                direction = st.radio(
                    "Scaling Function",
                    ["Maximize", "Minimize"],
                    index=0 if selected_attr.scaling_direction == "Maximize" else 1
                )
                if direction != selected_attr.scaling_direction:
                    selected_attr.scaling_direction = direction
                    st.rerun()

                st.info(f"Min: {selected_attr.min_val} {selected_attr.unit}")
                st.info(f"Max: {selected_attr.max_val} {selected_attr.unit}")

            elif scaling_type == "Custom":
                st.write("Define Custom Points (Raw Value, Score 0-1)")

                # Prepare DataFrame
                data = [{"Raw Value": p[0], "Score": p[1]} for p in selected_attr.custom_points]
                if not data:
                    # Default points
                    data = [
                        {"Raw Value": selected_attr.min_val, "Score": 0.0},
                        {"Raw Value": selected_attr.max_val, "Score": 1.0}
                    ]

                df = pd.DataFrame(data)

                edited_df = st.data_editor(
                    df,
                    key=f"scaling_editor_{selected_attr.id}",
                    num_rows="dynamic",
                    column_config={
                        "Raw Value": st.column_config.NumberColumn(required=True),
                        "Score": st.column_config.NumberColumn(min_value=0.0, max_value=1.0, step=0.01, required=True)
                    },
                    hide_index=True
                )

                # Update points
                new_points = []
                for _, row in edited_df.iterrows():
                    if not pd.isna(row["Raw Value"]) and not pd.isna(row["Score"]):
                        new_points.append((float(row["Raw Value"]), float(row["Score"])))

                # Check if changed
                if new_points != selected_attr.custom_points:
                    selected_attr.custom_points = new_points
                    # Since st.data_editor triggers rerun on change if key is not set or unique?
                    # Wait, st.data_editor returns the new state. We update the model.
                    # The graph below uses the model.
                    pass

        with col2:
            st.subheader("Value Function Graph")

            # Generate points for graph
            x_range = np.linspace(selected_attr.min_val, selected_attr.max_val, 100)
            y_values = [selected_attr.get_value(x) for x in x_range]

            fig = go.Figure()
            fig.add_trace(go.Scatter(x=x_range, y=y_values, mode='lines', name='Value Function'))

            # Add points if Custom
            if scaling_type == "Custom":
                custom_x = [p[0] for p in selected_attr.custom_points]
                custom_y = [p[1] for p in selected_attr.custom_points]
                fig.add_trace(go.Scatter(x=custom_x, y=custom_y, mode='markers', name='Defined Points'))

            fig.update_layout(
                title=f"Value Function for {selected_attr.name}",
                xaxis_title=f"Raw Value ({selected_attr.unit})",
                yaxis_title="Value Score (0-1)",
                yaxis_range=[-0.1, 1.1]
            )

            st.plotly_chart(fig, width='stretch')
