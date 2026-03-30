"""Redirects to unified Run Model page (VFT lives there)."""
import streamlit as st

import bootstrap  # noqa: F401

from app.ui_theme import apply_theme

st.set_page_config(page_title="MCDA — Run Model", layout="wide")
apply_theme()
st.switch_page("pages/3_run_models.py")
