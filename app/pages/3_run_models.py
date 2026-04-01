import bootstrap  # noqa: F401

import streamlit as st
from app.ui_theme import apply_theme, section_header
from app.app_context import guard_page, sync_method_from_scenario
from app.sidebar_nav import render_sidebar
from app.mcda_run_pages import render_topsis_run, render_vft_run
from persistence.engine import get_engine

st.set_page_config(page_title="MCDA — Run Model", layout="wide")
apply_theme()
st.title("STEP 3: RUN MODEL")

guard_page("pages/3_run_models.py", require_scenario=True)
sync_method_from_scenario()
render_sidebar("pages/3_run_models.py")

engine = get_engine()
scenario_id = st.session_state.get("scenario_id")
user_name = st.session_state.get("user_name", "")
method_choice = st.session_state.get("method_choice", "topsis")

if not scenario_id:
    st.warning("No scenario selected — go to Step 1.")
    if st.button("Go To Step 1"):
        st.switch_page("pages/1_decision_setup.py")
    st.stop()

section_header("Run Model", variant="gradient")
st.caption(f"Scenario method: **{method_choice.upper()}**")

if method_choice == "topsis":
    render_topsis_run(engine, scenario_id, user_name)
elif method_choice == "vft":
    render_vft_run(engine, scenario_id, user_name)
else:
    st.error(f"Unknown method: {method_choice!r}. Return to Step 1.")
    if st.button("← Step 1: Decision & Scenario"):
        st.switch_page("pages/1_decision_setup.py")
