import streamlit as st

from app.app_context import get_active_flow, get_active_method


def _render_dev_sidebar_controls():
    """Rerun and dev hints (replaces the hidden top developer toolbar)."""
    with st.sidebar.expander("App", expanded=False):
        st.caption(
            "The top bar (Deploy, menu) is hidden for a cleaner layout. "
            "Use **Rerun** here after edits."
        )
        if st.button("Rerun app", use_container_width=True, key="mcda_sidebar_rerun"):
            st.rerun()
        st.caption(
            "Auto-rerun on save: set `runOnSave = true` under `[server]` in `.streamlit/config.toml`."
        )


def render_sidebar(current_page_path: str | None = None):
    method = get_active_method()
    if method:
        flow = get_active_flow()

        st.sidebar.markdown("## MCDA FLOW")
        st.sidebar.caption(f"Method: {method.upper()}")
        st.sidebar.divider()

        current_idx = None
        for idx, (_, _, path, _) in enumerate(flow, start=1):
            if path == current_page_path:
                current_idx = idx
                break
        if current_idx is not None:
            st.sidebar.caption(f"Step {current_idx} of {len(flow)}")
            st.sidebar.progress(current_idx / len(flow))
            st.sidebar.divider()

        for idx, (_, label, path, _) in enumerate(flow, start=1):
            if path == current_page_path:
                st.sidebar.markdown(
                    f"<div class='sidebar-active-item'>STEP {idx}. {label}</div>",
                    unsafe_allow_html=True,
                )
            else:
                st.sidebar.page_link(path, label=f"STEP {idx}. {label.upper()}")

        st.sidebar.divider()

        if st.sidebar.button("RESET / CHANGE METHOD", use_container_width=True):
            for key in ["scenario_id", "decision_id", "method_choice", "selected_run_id"]:
                if key in st.session_state:
                    del st.session_state[key]
            st.switch_page("pages/1_decision_setup.py")

    _render_dev_sidebar_controls()
