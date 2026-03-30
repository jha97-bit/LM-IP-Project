import bootstrap  # noqa: F401

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from app.ui_theme import apply_theme, BLUE_SCALE, TEAL_SCALE, BLUE_TEAL_SCALE, DISCRETE_PALETTE
from app.app_context import guard_page, sync_method_from_scenario
from app.sidebar_nav import render_sidebar

from persistence.engine import get_engine
from persistence.repositories.criterion_repo import CriterionRepo
from persistence.repositories.measurement_repo import MeasurementRepo
from services.vft_service import VFTService
from core.vft_model import Attribute

st.set_page_config(page_title="MCDA — VFT Value Functions", layout="wide")
apply_theme()
st.title("Step 3b: Value Functions (VFT)")

guard_page("pages/3b_vft_value_functions.py", require_scenario=True)
sync_method_from_scenario()
render_sidebar("pages/3b_vft_value_functions.py")

engine = get_engine()
scenario_id = st.session_state.get("scenario_id")

if st.session_state.get("method_choice") != "vft":
    st.warning("This page is only for VFT scenarios.")
    st.switch_page("pages/1_decision_setup.py")

user_name = st.session_state.get("user_name", "")

if not scenario_id:
    st.warning("No scenario selected - go to Step 1.")
    if st.button("← Go to Step 1", key="vf_goto_step1"):
        st.switch_page("pages/1_decision_setup.py")
    st.stop()

crit_repo = CriterionRepo(engine)
meas_repo = MeasurementRepo(engine)
vft_svc = VFTService(engine)

# ─── Navigation ───────────────────────────────────────────────────────────────
nav_left, nav_right = st.columns(2)
with nav_left:
    if st.button("← Step 2: Data Input", key="vf_nav_back"):
        st.switch_page("pages/2_data_input.py")
with nav_right:
    if st.button("Next: Run VFT →", type="primary", key="vf_nav_next"):
        st.switch_page("pages/3_run_models.py")

st.caption("Define how raw values map to utility scores (0-1) for **each criterion**. "
           "Save each one individually, then proceed to Run VFT.")
st.divider()

existing_crit = crit_repo.list_by_scenario(scenario_id)
if not existing_crit:
    st.warning("No criteria found. Go to Step 2 and save alternatives & criteria first.")
    st.stop()

existing_vfs = vft_svc.load_value_functions(scenario_id)
matrix_df = meas_repo.load_matrix_ui(scenario_id)
crit_names = [c["name"] for c in existing_crit]

# ─── Overview status bar ──────────────────────────────────────────────────────
st.subheader("📋 Criteria Overview")
overview_rows = []
for crit in existing_crit:
    cname = crit["name"]
    vf = existing_vfs.get(cname, {})
    direction_display = "Maximize ↑" if crit.get("direction") == "benefit" else "Minimize ↓"
    if vf:
        pts = vf.get("points", [])
        ft = vf.get("function_type", "—")
        status = "✅ Configured"
    else:
        pts = []
        ft = "—"
        status = "⚠️ Not configured"
    overview_rows.append({
        "Criterion": cname,
        "Direction": direction_display,
        "Function Type": ft,
        "# Points": len(pts),
        "Status": status,
    })

if overview_rows:
    st.dataframe(pd.DataFrame(overview_rows), use_container_width=True, hide_index=True)

not_configured = [r["Criterion"] for r in overview_rows if "⚠️" in r["Status"]]
if not_configured:
    st.warning(f"Not yet configured: **{', '.join(not_configured)}**. "
               "Unconfigured criteria will use a default linear (increasing) function when running VFT.")
else:
    st.success("✅ All criteria have value functions configured. Ready to run VFT.")

st.divider()

# ─── Per-criterion configurator ───────────────────────────────────────────────
st.subheader("Configure Value Function")
st.caption("Select a criterion from the tabs below and define its value function, then click Save.")

crit_tabs = st.tabs([f"{'✅' if existing_vfs.get(c['name']) else '⚙️'} {c['name']}" for c in existing_crit])

for tab_idx, (tab, crit) in enumerate(zip(crit_tabs, existing_crit)):
    with tab:
        selected_crit_name = crit["name"]
        selected_crit = crit

        # Data range from matrix
        if not matrix_df.empty and selected_crit_name in matrix_df.columns:
            data_min = float(matrix_df[selected_crit_name].min())
            data_max = float(matrix_df[selected_crit_name].max())
        else:
            data_min = 0.0
            data_max = 100.0

        existing_vf = existing_vfs.get(selected_crit_name, {})
        existing_pts = existing_vf.get("points", [])
        existing_ft = existing_vf.get("function_type", "linear")

        col_cfg, col_chart = st.columns([1, 2], gap="large")

        with col_cfg:
            st.markdown(f"**Criterion:** {selected_crit_name}")
            dir_display = "Maximize ↑" if selected_crit.get("direction") == "benefit" else "Minimize ↓"
            st.caption(f"Direction: {dir_display} · Data range: `{data_min:.3f}` - `{data_max:.3f}` "
                       f"{selected_crit.get('unit') or ''}")

            scaling_type = st.selectbox(
                "Scaling type",
                ["Linear", "Custom (Piecewise)"],
                index=0 if existing_ft == "linear" else 1,
                key=f"scale_type_{tab_idx}_{selected_crit_name}",
            )
            is_linear = scaling_type == "Linear"

            if is_linear:
                direction = st.radio(
                    "Value function direction",
                    ["Increasing (higher raw → higher utility)",
                     "Decreasing (lower raw → higher utility)"],
                    index=0 if selected_crit.get("direction") == "benefit" else 1,
                    key=f"vf_dir_{tab_idx}_{selected_crit_name}",
                )
                is_increasing = "Increasing" in direction

                # Ask for explicit min/max for linear function
                lin_col1, lin_col2 = st.columns(2)
                with lin_col1:
                    lin_min = st.number_input(
                        "Raw minimum (maps to 0.0 utility)",
                        value=data_min,
                        key=f"lin_min_{tab_idx}_{selected_crit_name}",
                        format="%.4f",
                    )
                with lin_col2:
                    lin_max = st.number_input(
                        "Raw maximum (maps to 1.0 utility)",
                        value=data_max,
                        key=f"lin_max_{tab_idx}_{selected_crit_name}",
                        format="%.4f",
                    )

                custom_points = None

            else:
                st.caption("Define breakpoints (raw value, utility). Intermediate values are linearly interpolated.")

                if existing_pts and existing_ft == "piecewise_linear":
                    default_data = [{"Raw Value": p[0], "Score (0-1)": p[1]} for p in existing_pts]
                else:
                    default_data = [
                        {"Raw Value": data_min, "Score (0-1)": 0.0 if selected_crit.get("direction") == "benefit" else 1.0},
                        {"Raw Value": (data_min + data_max) / 2, "Score (0-1)": 0.5},
                        {"Raw Value": data_max, "Score (0-1)": 1.0 if selected_crit.get("direction") == "benefit" else 0.0},
                    ]

                pts_df = st.data_editor(
                    pd.DataFrame(default_data), num_rows="dynamic", use_container_width=True,
                    key=f"vf_pts_{tab_idx}_{selected_crit_name}",
                    column_config={
                        "Raw Value": st.column_config.NumberColumn(required=True, format="%.4f"),
                        "Score (0-1)": st.column_config.NumberColumn(required=True, min_value=0.0, max_value=1.0, format="%.3f"),
                    },
                )
                custom_points = []
                for _, row in pts_df.iterrows():
                    rv, sc = row.get("Raw Value"), row.get("Score (0-1)")
                    if rv is not None and sc is not None and not pd.isna(rv) and not pd.isna(sc):
                        custom_points.append((float(rv), float(sc)))
                custom_points = sorted(custom_points, key=lambda p: p[0])

            if st.button(f"💾 Save Value Function", type="primary",
                         key=f"btn_save_vf_{tab_idx}_{selected_crit_name}"):
                if is_linear:
                    if lin_max <= lin_min:
                        st.error("Raw maximum must be greater than raw minimum for a linear value function.")
                        st.stop()

                    attr = Attribute(
                        name=selected_crit_name,
                        min_val=lin_min,
                        max_val=lin_max,
                        scaling_type="Linear",
                        scaling_direction="Increasing" if is_increasing else "Decreasing",
                    )
                else:
                    if len(custom_points) < 2:
                        st.error("Define at least 2 control points.")
                        st.stop()
                    attr = Attribute(
                        name=selected_crit_name,
                        min_val=data_min, max_val=data_max,
                        scaling_type="Custom",
                        custom_points=custom_points or [],
                    )

                crit_map = {c["name"]: c["criterion_id"] for c in existing_crit}
                vft_svc.save_value_functions(
                    scenario_id=scenario_id,
                    crit_map=crit_map,
                    attributes=[attr],
                    created_by=user_name,
                )
                st.toast(f"✅ Value function saved for '{selected_crit_name}'!", icon="📈")
                st.rerun()

        with col_chart:
            st.markdown(f"**Value Function Graph - {selected_crit_name}**")

            # Build plot attribute
            if is_linear:
                plot_min = lin_min if 'lin_min' in dir() else data_min
                plot_max = lin_max if 'lin_max' in dir() else data_max
                plot_direction = "Increasing" if 'is_increasing' not in dir() or is_increasing else "Decreasing"

                if plot_max <= plot_min:
                    plot_max = plot_min + 1.0

                attr_plot = Attribute(
                    name=selected_crit_name,
                    min_val=plot_min,
                    max_val=plot_max,
                    scaling_type="Linear",
                    scaling_direction=plot_direction,
                )
                plot_pts = None
            else:
                attr_plot = Attribute(
                    name=selected_crit_name,
                    min_val=data_min,
                    max_val=data_max,
                    scaling_type="Custom",
                    custom_points=custom_points or [],
                )
                plot_pts = custom_points or []

            # Build the main value-function line as a true pairwise linear plot.
            x_min = min(data_min, attr_plot.min_val)
            x_max = max(data_max, attr_plot.max_val)
            if np.isclose(x_min, x_max):
                x_min -= 1
                x_max += 1

            if plot_pts and len(plot_pts) >= 2:
                line_x = [p[0] for p in sorted(plot_pts, key=lambda pt: pt[0])]
                line_y = [p[1] for p in sorted(plot_pts, key=lambda pt: pt[0])]
            else:
                line_x = [attr_plot.min_val, attr_plot.max_val]
                try:
                    line_y = [attr_plot.get_value(attr_plot.min_val), attr_plot.get_value(attr_plot.max_val)]
                except Exception:
                    line_y = [0.0, 1.0]

            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=line_x, y=line_y, mode="lines", name="Value Function",
                line=dict(color="#2563eb", width=3),
            ))

            if plot_pts and len(plot_pts) >= 2:
                fig.add_trace(go.Scatter(
                    x=[p[0] for p in sorted(plot_pts, key=lambda pt: pt[0])], y=[p[1] for p in sorted(plot_pts, key=lambda pt: pt[0])],
                    mode="markers", name="Control Points",
                    marker=dict(color="#6366f1", size=10, symbol="circle"),
                ))

            # Actual alternative points projected onto the same value function.
            if not matrix_df.empty and selected_crit_name in matrix_df.columns:
                actual_series = matrix_df[selected_crit_name].dropna()
                try:
                    actual_vals = actual_series.astype(float).tolist()
                    actual_utilities = [attr_plot.get_value(v) for v in actual_vals]
                    alt_names = actual_series.index.tolist()
                    fig.add_trace(go.Scatter(
                        x=actual_vals, y=actual_utilities, mode="markers+text",
                        text=alt_names,
                        textposition="top right",
                        name="Alternatives",
                        marker=dict(color="#16a34a", size=10, symbol="diamond"),
                    ))
                except Exception:
                    pass

            fig.update_layout(
                xaxis_title=f"Raw Value ({selected_crit.get('unit') or ''})",
                yaxis_title="Utility Score (0 - 1)",
                yaxis=dict(range=[-0.05, 1.1]),
                height=360,
                margin=dict(l=0, r=0, t=10, b=10),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(248,250,252,1)",
            )
            fig.update_xaxes(showgrid=True, gridcolor="rgba(0,0,0,0.06)")
            fig.update_yaxes(showgrid=True, gridcolor="rgba(0,0,0,0.06)")
            st.plotly_chart(fig, use_container_width=True, key=f"vf_chart_{tab_idx}_{selected_crit_name}")

st.divider()
col_prev, col_next = st.columns(2)
with col_prev:
    if st.button("← Step 2: Data Input", key="vf_bottom_back"):
        st.switch_page("pages/2_data_input.py")
with col_next:
    if st.button("Next: Run VFT →", type="primary", key="vf_bottom_next"):
        st.switch_page("pages/3_run_models.py")
