import bootstrap  # noqa: F401

import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Internal MCDA Tool",
    page_icon="📊",
    layout="wide",
)

st.title("Internal MCDA Tool")
st.caption("Build a decision model with traceable inputs, run methods, and store every run for audit.")

st.divider()

# ----------------------------
# Start (Attribution)
# ----------------------------
st.subheader("Start")
st.write("Enter your name for attribution in runs and history.")

default_name = st.session_state.get("user_name", "Atharva")
user_name = st.text_input("Your name", value=default_name, placeholder="Atharva")
st.session_state["user_name"] = (user_name or "").strip()

start_cols = st.columns([1, 1, 2])
with start_cols[0]:
    go_step1 = st.button("Start building", type="primary", disabled=not st.session_state["user_name"])
with start_cols[1]:
    go_results = st.button("View results", disabled=not st.session_state.get("scenario_id"))

if go_step1:
    st.switch_page("pages/1_decision_setup.py")

if go_results:
    st.switch_page("pages/4_results.py")

st.divider()

# ----------------------------
# Methods
# ----------------------------
st.header("Methods")
st.write("Understand how ranking is computed and what is stored for audit.")

mcol1, mcol2 = st.columns(2)

with mcol1:
    st.subheader("TOPSIS")
    st.success("Available in MVP")
    st.write(
        "Ranks alternatives by closeness to the ideal best option and distance from the ideal worst option."
    )

    st.markdown("**High level steps:**")
    st.markdown(
        """
        1. Normalize the matrix  
        2. Apply weights  
        3. Compute ideal best and ideal worst  
        4. Compute distances S+ and S-  
        5. Compute closeness score C* and rank
        """
    )

with mcol2:
    st.subheader("VFT")
    st.info("Coming next")
    st.write(
        "Converts raw measurements into utilities using value functions, then sums weighted utilities."
    )

    st.markdown("**High level steps:**")
    st.markdown(
        """
        1. Define a value function per criterion  
        2. Convert x to u(x) in range 0..1  
        3. Multiply by weight  
        4. Sum utilities and rank
        """
    )

st.divider()

# ----------------------------
# Example
# ----------------------------
st.header("Example")
st.write("A small sample to show how inputs map to scores and ranking.")

st.subheader("Small example")
st.caption("2 criteria, 3 alternatives. Weights: Cost 0.6, Quality 0.4")

example_df = pd.DataFrame(
    {
        "Alternative": ["A", "B", "C"],
        "Cost (lower better)": [100, 120, 80],
        "Quality (higher better)": [70, 90, 60],
    }
)

st.dataframe(example_df, use_container_width=True)

st.write(
    "TOPSIS outputs a score C* and ranking. VFT maps each measurement into a 0..1 utility first, "
    "then produces a weighted total score and ranking."
)

st.divider()

# ----------------------------
# MVP Scope
# ----------------------------
st.header("MVP Scope")
st.write("What you can do today, and what is coming next.")

scope_col1, scope_col2 = st.columns(2)

with scope_col1:
    st.subheader("What the MVP offers")
    st.markdown(
        """
        - Decision and Scenario setup  
        - Alternatives and Criteria entry  
        - Preference sets with direct weights  
        - Performance matrix entry  
        - Run TOPSIS and store results  
        - Results view with run metadata  
        - History and compare runs
        """
    )

with scope_col2:
    st.subheader("Coming next")
    st.markdown(
        """
        - VFT value functions and utility contribution views  
        - Sensitivity analysis  
        - AHP and QFD extensions
        """
    )

st.divider()

# ----------------------------
# Governance
# ----------------------------
st.header("Governance and auditability")

g1, g2 = st.columns(2)
with g1:
    st.markdown("**Database is the source of truth**")
    st.write("Inputs, runs, and derived artifacts are stored and retrieved from the database.")

with g2:
    st.markdown("**Runs store key metadata**")
    st.write("Runs store executed_by, executed_at, and engine_version to support traceability.")

st.write("History supports traceability and comparisons.")
