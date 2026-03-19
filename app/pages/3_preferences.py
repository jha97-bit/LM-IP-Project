import bootstrap  # noqa: F401

import streamlit as st
from app.ui_theme import apply_theme, BLUE_SCALE, TEAL_SCALE, BLUE_TEAL_SCALE, DISCRETE_PALETTE

from app.app_context import get_active_method, sync_method_from_scenario

sync_method_from_scenario()
method_choice = get_active_method()
apply_theme()

if not method_choice:
    st.title("Step 3: Analysis")
    st.warning("No method selected. Please go back to Step 1 and choose TOPSIS or VFT.")
    if st.button("← Go to Step 1"):
        st.switch_page("pages/1_decision_setup.py")
    st.stop()

if method_choice == "vft":
    st.switch_page("pages/3b_vft_value_functions.py")
else:
    st.switch_page("pages/3a_run_topsis.py")
