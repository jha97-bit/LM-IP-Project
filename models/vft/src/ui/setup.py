import streamlit as st
import pandas as pd
from src.model import Attribute, Alternative

def render_setup_ui(model):
    st.header("Model Setup")

    tab1, tab2 = st.tabs(["Objectives / Attributes", "Alternatives"])

    with tab1:
        st.subheader("Manage Objectives and Attributes")

        # Prepare DataFrame
        data = []
        for attr in model.attributes:
            data.append({
                "ID": attr.id,
                "Name": attr.name,
                "Min": attr.min_val,
                "Max": attr.max_val,
                "Unit": attr.unit,
                "Weight": attr.weight # Allow editing weight here too? Maybe just read-only or basic edit.
            })

        if not data:
            df = pd.DataFrame(columns=["ID", "Name", "Min", "Max", "Unit", "Weight"])
        else:
            df = pd.DataFrame(data)

        # Editor
        edited_df = st.data_editor(
            df,
            key="attributes_editor",
            num_rows="dynamic",
            column_order=["Name", "Min", "Max", "Unit", "Weight"],
            column_config={
                "ID": st.column_config.TextColumn(disabled=True),
                "Name": st.column_config.TextColumn(required=True),
                "Min": st.column_config.NumberColumn(required=True, default=0.0),
                "Max": st.column_config.NumberColumn(required=True, default=100.0),
                "Unit": st.column_config.TextColumn(),
                "Weight": st.column_config.NumberColumn(min_value=0.0, max_value=1.0, step=0.01)
            },
            hide_index=True
        )

        # Update Model
        if st.button("Update Attributes"):
            current_ids = set()

            # Update or Add
            for index, row in edited_df.iterrows():
                attr_id = row.get("ID")
                name = row["Name"]
                min_val = row["Min"]
                max_val = row["Max"]
                unit = row["Unit"]
                weight = row["Weight"]

                if pd.isna(attr_id) or attr_id == "":
                    # New Attribute
                    new_attr = Attribute(name, min_val=min_val, max_val=max_val, unit=unit, weight=weight)
                    model.add_attribute(new_attr)
                    current_ids.add(new_attr.id)
                else:
                    # Existing Attribute
                    # Find it
                    existing = next((a for a in model.attributes if a.id == attr_id), None)
                    if existing:
                        existing.name = name
                        existing.min_val = float(min_val)
                        existing.max_val = float(max_val)
                        existing.unit = unit
                        existing.weight = float(weight)
                        current_ids.add(existing.id)

            # But we must only delete if the user explicitly removed them from the editor.
            # The edited_df contains the *desired* state. So anything not in it should be removed.

            # Identify IDs to remove
            existing_ids = set(a.id for a in model.attributes)
            ids_to_remove = existing_ids - current_ids

            for i in ids_to_remove:
                # Find name to use remove_attribute
                attr_to_remove = next((a for a in model.attributes if a.id == i), None)
                if attr_to_remove:
                    model.remove_attribute(attr_to_remove.name)

            st.success("Attributes updated successfully!")
            st.rerun()

    with tab2:
        st.subheader("Manage Alternatives")

        # Prepare DataFrame
        data = []
        for alt in model.alternatives:
            data.append({
                "ID": alt.id,
                "Name": alt.name
            })

        if not data:
            df = pd.DataFrame(columns=["ID", "Name"])
        else:
            df = pd.DataFrame(data)

        edited_df = st.data_editor(
            df,
            key="alternatives_editor",
            num_rows="dynamic",
            column_order=["Name"],
            column_config={
                "ID": st.column_config.TextColumn(disabled=True),
                "Name": st.column_config.TextColumn(required=True)
            },
            hide_index=True
        )

        if st.button("Update Alternatives"):
            current_ids = set()

            for index, row in edited_df.iterrows():
                alt_id = row.get("ID")
                name = row["Name"]

                if pd.isna(alt_id) or alt_id == "":
                    new_alt = Alternative(name)
                    model.add_alternative(new_alt)
                    current_ids.add(new_alt.id)
                else:
                    existing = next((a for a in model.alternatives if a.id == alt_id), None)
                    if existing:
                        existing.name = name
                        current_ids.add(existing.id)

            existing_ids = set(a.id for a in model.alternatives)
            ids_to_remove = existing_ids - current_ids

            for i in ids_to_remove:
                alt_to_remove = next((a for a in model.alternatives if a.id == i), None)
                if alt_to_remove:
                    model.remove_alternative(alt_to_remove.name)

            st.success("Alternatives updated successfully!")
            st.rerun()
