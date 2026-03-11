import streamlit as st
st.set_page_config(page_title="VFT App", layout="wide")

from src.model import VFTModel
from src.ui.setup import render_setup_ui
from src.ui.scaling import render_scaling_ui
from src.ui.weighting import render_weighting_ui
from src.ui.analysis import render_analysis_ui
from src.ui.comparison import render_comparison_ui
from src.ui.sensitivity import render_sensitivity_ui

# Initialize Session State
if "model" not in st.session_state:
    st.session_state.model = VFTModel()
st.title("Value-Focused Thinking (VFT) Application")

# Sidebar Navigation
page = st.sidebar.radio("Navigation", ["Setup", "Scaling", "Weighting", "Scoring & Analysis", "Comparison", "Sensitivity Analysis"])

st.sidebar.markdown("---")
st.sidebar.header("Model Management")

# Save Model
model_json = st.session_state.model.to_json()
st.sidebar.download_button(
    label="Download Model (JSON)",
    data=model_json,
    file_name="vft_model.json",
    mime="application/json"
)

# Load Model
uploaded_file = st.sidebar.file_uploader("Load Model (JSON)", type=["json"], key="model_loader")
if uploaded_file is not None:
    # Check if this file was already processed to avoid overwriting changes on rerun
    if "last_uploaded_file" not in st.session_state or st.session_state.last_uploaded_file != uploaded_file:
        try:
            json_str = uploaded_file.getvalue().decode("utf-8")
            st.session_state.model = VFTModel.from_json(json_str)
            st.session_state.last_uploaded_file = uploaded_file
            st.sidebar.success("Model loaded successfully!")
            st.rerun()
        except Exception as e:
            st.sidebar.error(f"Error loading model: {e}")

if page == "Setup":
    render_setup_ui(st.session_state.model)
elif page == "Scaling":
    render_scaling_ui(st.session_state.model)
elif page == "Weighting":
    render_weighting_ui(st.session_state.model)
elif page == "Scoring & Analysis":
    render_analysis_ui(st.session_state.model)
elif page == "Comparison":
    render_comparison_ui(st.session_state.model)
elif page == "Sensitivity Analysis":
    render_sensitivity_ui(st.session_state.model)
