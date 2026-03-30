import bootstrap  # noqa: F401

import streamlit as st
from app.ui_theme import apply_theme
from app.app_context import guard_page, sync_method_from_scenario
from app.sidebar_nav import render_sidebar
from app.mcda_run_pages import render_ahp_placeholder, render_topsis_run, render_vft_run
from persistence.engine import get_engine

st.set_page_config(page_title="MCDA — Run Model", layout="wide")
apply_theme()
st.title("Step 3: Run Model")

guard_page("pages/3_run_models.py", require_scenario=True)
sync_method_from_scenario()
render_sidebar("pages/3_run_models.py")

engine = get_engine()
scenario_id = st.session_state.get("scenario_id")
user_name = st.session_state.get("user_name", "")
method_choice = st.session_state.get("method_choice", "topsis")

if not scenario_id:
    st.warning("No scenario selected — go to Step 1.")
    if st.button("← Go to Step 1"):
        st.switch_page("pages/1_decision_setup.py")
    st.stop()

st.caption(f"Scenario method: **{method_choice.upper()}**")
st.divider()

if method_choice == "topsis":
    render_topsis_run(engine, scenario_id, user_name)
elif method_choice == "vft":
    render_vft_run(engine, scenario_id, user_name)
elif method_choice == "ahp":
    render_ahp_placeholder()
else:
    st.error(f"Unknown method: {method_choice!r}. Return to Step 1.")
    if st.button("← Step 1: Decision & Scenario"):
        st.switch_page("pages/1_decision_setup.py")
