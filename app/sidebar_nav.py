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


def _render_sidebar_step_progress(current_idx: int, flow_len: int) -> None:
    """HTML/CSS bar so the gray track and teal fill are both visible (st.progress Base Web styling was collapsing)."""
    pct = 0.0 if flow_len <= 0 else min(1.0, max(0.0, current_idx / flow_len))
    st.markdown(
        f"""
<div class="mcda-sidebar-progress-wrap" aria-hidden="true">
  <div class="mcda-sidebar-progress-track">
    <div class="mcda-sidebar-progress-fill" style="width:{pct * 100:.4f}%"></div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )


def render_sidebar(current_page_path: str | None = None):
    with st.sidebar:
        with st.spinner("Loading session…"):
            method = get_active_method()

        if method:
            flow = get_active_flow()

            st.markdown("## MCDA FLOW")
            st.caption(f"Method: {method.upper()}")
            st.divider()

            current_idx = None
            for idx, (_, _, path, _) in enumerate(flow, start=1):
                if path == current_page_path:
                    current_idx = idx
                    break
            if current_idx is not None:
                st.caption(f"Step {current_idx} of {len(flow)}")
                _render_sidebar_step_progress(current_idx, len(flow))
                st.divider()

            for idx, (_, label, path, _) in enumerate(flow, start=1):
                if path == current_page_path:
                    st.markdown(
                        f"<div class='sidebar-active-item'>STEP {idx}. {label}</div>",
                        unsafe_allow_html=True,
                    )
                else:
                    st.page_link(path, label=f"STEP {idx}. {label.upper()}")

            st.divider()

            if st.button("RESET / CHANGE METHOD", use_container_width=True):
                for key in ["scenario_id", "decision_id", "method_choice", "selected_run_id"]:
                    if key in st.session_state:
                        del st.session_state[key]
                st.switch_page("pages/1_decision_setup.py")

    _render_dev_sidebar_controls()
