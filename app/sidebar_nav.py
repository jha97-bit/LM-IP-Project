import streamlit as st

from app.app_context import get_active_flow, get_active_method


def render_sidebar(current_page_path: str | None = None):
    method = get_active_method()
    if not method:
        return

    flow = get_active_flow()

    st.sidebar.markdown("## MCDA Flow")
    st.sidebar.caption(f"Method: {method.upper()}")
    st.sidebar.divider()

    for idx, (_, label, path, icon) in enumerate(flow, start=1):
        if path == current_page_path:
            st.sidebar.markdown(f"**Step {idx}. {icon} {label}**")
        else:
            st.sidebar.page_link(path, label=f"Step {idx}. {label}", icon=icon)

    st.sidebar.divider()

    if st.sidebar.button("Reset / Change Method", use_container_width=True):
        for key in ["scenario_id", "decision_id", "method_choice", "selected_run_id"]:
            if key in st.session_state:
                del st.session_state[key]
        st.switch_page("pages/1_decision_setup.py")
