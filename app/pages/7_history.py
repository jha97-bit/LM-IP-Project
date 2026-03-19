# app/pages/7_history.py
import bootstrap  # noqa: F401

import streamlit as st
from app.ui_theme import apply_theme, BLUE_SCALE, TEAL_SCALE, BLUE_TEAL_SCALE, DISCRETE_PALETTE
from app.app_context import guard_page, sync_method_from_scenario
from app.sidebar_nav import render_sidebar
import pandas as pd
from sqlalchemy import text

from persistence.engine import get_engine
from services.delete_service import DeleteService
from services.scenario_share_service import ScenarioShareService

st.set_page_config(page_title="MCDA — History", layout="wide")
apply_theme()
st.title("Step 7: History, Logs & Export")

guard_page("pages/7_history.py", require_scenario=True)
sync_method_from_scenario()
render_sidebar("pages/7_history.py")

engine = get_engine()
deleter = DeleteService(engine)
sharer = ScenarioShareService(engine)

scenario_id = st.session_state.get("scenario_id")
if not scenario_id:
    st.info("Go to Step 1 and select a Scenario first.")
    st.stop()

# Navigation
nav_left, nav_right = st.columns(2)
with nav_left:
    if st.button("← Back: Step 6 (Report Builder)"):
        st.switch_page("pages/6_report_builder.py")
with nav_right:
    if st.button("⇤ Return to Step 1"):
        st.switch_page("pages/1_decision_setup.py")

st.divider()

# ----------------------------
# Fetch current decision_id
# ----------------------------
with engine.begin() as conn:
    row = conn.execute(
        text("""
            SELECT decision_id::text AS decision_id, s.name AS scenario_name,
                   d.title AS decision_title
            FROM scenarios s
            JOIN decisions d USING (decision_id)
            WHERE scenario_id = :sid
        """),
        {"sid": scenario_id},
    ).mappings().first()

decision_id = row["decision_id"] if row else None
scenario_name = row["scenario_name"] if row else "Unknown Scenario"
decision_title = row["decision_title"] if row else "Unknown Decision"

st.caption(f"📋 Decision: **{decision_title}** | Scenario: **{scenario_name}**")

# ----------------------------
# Preference set name map
# ----------------------------
with engine.begin() as conn:
    pref_rows = conn.execute(
        text("""
            SELECT preference_set_id::text AS preference_set_id, name
            FROM preference_sets
            WHERE scenario_id = :sid
        """),
        {"sid": scenario_id},
    ).mappings().all()

pref_id_to_name = {r["preference_set_id"]: r["name"] for r in pref_rows}

# ----------------------------
# Runs table
# ----------------------------
st.subheader("Run History (Current Scenario)")

with engine.begin() as conn:
    cols = conn.execute(
        text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema='public' AND table_name='runs'
        """)
    ).fetchall()
    run_cols = {c[0] for c in cols}

has_run_label = "run_label" in run_cols

select_sql = """
    SELECT
        run_id::text AS run_id,
        executed_at,
        method,
        preference_set_id::text AS preference_set_id,
        executed_by
"""
if has_run_label:
    select_sql += ", run_label"
else:
    select_sql += ", NULL::text AS run_label"

select_sql += """
    FROM runs
    WHERE scenario_id = :sid
    ORDER BY executed_at DESC
    LIMIT 200
"""

with engine.begin() as conn:
    runs = conn.execute(text(select_sql), {"sid": scenario_id}).mappings().all()

runs = [dict(r) for r in runs]
if not runs:
    st.info("No runs yet for this scenario.")
else:
    runs_df = pd.DataFrame(runs)
    runs_df["preference_set_name"] = runs_df["preference_set_id"].map(
        lambda x: pref_id_to_name.get(x, x[:8] + "…" if x else "—")
    )
    display_cols = ["executed_at", "method", "preference_set_name", "executed_by", "run_label", "run_id"]
    runs_df_display = runs_df[display_cols]

    st.dataframe(runs_df_display, use_container_width=True)

    st.download_button(
        "⬇ Download History CSV",
        data=runs_df_display.to_csv(index=False).encode("utf-8"),
        file_name=f"run_history_{scenario_id[:8]}.csv",
        mime="text/csv",
    )

    st.divider()

    # ----------------------------
    # Select a run for actions
    # ----------------------------
    st.subheader("Open or Manage a Run")

    run_options = runs_df["run_id"].tolist()

    def _label_from_run_id(rid: str) -> str:
        r = next((rr for rr in runs if rr["run_id"] == rid), None)
        if not r:
            return rid
        pref_name = pref_id_to_name.get(r["preference_set_id"], (r["preference_set_id"] or "")[:8] + "…")
        base = f"{r['executed_at']} | {str(r['method']).upper()} | {pref_name}"
        if r.get("executed_by"):
            base += f" | {r['executed_by']}"
        if r.get("run_label"):
            base = f"{r['run_label']} | " + base
        return base

    default_run = (
        [st.session_state.get("last_run_id")]
        if st.session_state.get("last_run_id") in run_options
        else [run_options[0]]
    )

    picked = st.multiselect(
        "Pick a run",
        options=run_options,
        max_selections=1,
        default=default_run,
        format_func=_label_from_run_id,
        key=f"history_run_pick_{scenario_id}",
    )
    run_id = picked[0] if picked else run_options[0]

    with engine.begin() as conn:
        meta = conn.execute(
            text("""
                SELECT
                    run_id::text AS run_id,
                    scenario_id::text AS scenario_id,
                    preference_set_id::text AS preference_set_id,
                    method,
                    executed_at,
                    executed_by
                FROM runs
                WHERE run_id = :rid
            """),
            {"rid": run_id},
        ).mappings().first()

    if meta:
        btn1, btn2, btn3 = st.columns([1, 1, 2])

        with btn1:
            if st.button("📊 Go to Results"):
                st.session_state["scenario_id"] = meta["scenario_id"]
                st.session_state["preference_set_id"] = meta["preference_set_id"]
                st.session_state["last_run_id"] = meta["run_id"]
                st.switch_page("pages/4_results.py")

        with btn2:
            if st.button("🔁 Load this build"):
                st.session_state["scenario_id"] = meta["scenario_id"]
                st.session_state["preference_set_id"] = meta["preference_set_id"]
                st.session_state["last_run_id"] = meta["run_id"]
                st.success("Loaded build into session. Go to Step 4 to view results or Step 3 to rerun.")

        with btn3:
            st.caption('Tip: "Load this build" sets Scenario + Preference Set + Run for fast return to your exact results.')

    st.divider()

    # ----------------------------
    # Delete run (double confirmation)
    # ----------------------------
    st.subheader("Delete Run")

    token = f"DELETE {run_id[:8]}"
    st.warning(
        "This deletes the run and all generated artifacts for that run (TOPSIS or VFT). "
        "It does **not** delete your scenario inputs."
    )

    ack = st.checkbox("I understand this is permanent", value=False, key=f"ack_run_{run_id}")
    typed = st.text_input(f"Type to confirm: `{token}`", value="", key=f"type_run_{run_id}")

    can_delete = ack and typed.strip() == token

    if st.button("🗑 Delete this run", type="primary", disabled=not can_delete, key=f"btn_del_run_{run_id}"):
        res = deleter.delete_run(run_id)
        if res.ok:
            if st.session_state.get("last_run_id") == run_id:
                st.session_state["last_run_id"] = None
            st.success(res.message)
            st.rerun()
        else:
            st.warning(res.message)

st.divider()

# ----------------------------
# Export / Share Scenario (.mcda)
# ----------------------------
st.subheader("📦 Export Scenario")

st.info(
    "Export this scenario as a `.mcda` file — a portable snapshot containing all inputs, "
    "preference sets, value functions, and run results. "
    "Share it with a colleague or import it back into any instance of this tool."
)

if st.button("Generate .mcda export"):
    with st.spinner("Packaging scenario…"):
        try:
            mcda_bytes = sharer.export_scenario(scenario_id)
            fname = f"{scenario_name.replace(' ', '_')}_{scenario_id[:8]}.mcda"
            st.download_button(
                label="⬇ Download .mcda file",
                data=mcda_bytes,
                file_name=fname,
                mime="application/octet-stream",
            )
            st.success(f"Ready: **{fname}** ({len(mcda_bytes):,} bytes compressed)")
        except Exception as exc:
            st.warning(f"Export failed: {exc}")

st.divider()

# ----------------------------
# Danger Zone
# ----------------------------
with st.expander("⚠️ Danger zone: delete scenario or decision", expanded=False):
    st.warning("These actions permanently delete inputs and all history. This **cannot** be undone.")

    if decision_id:
        st.caption(f"Current scenario_id: `{scenario_id}`")
        st.caption(f"Current decision_id: `{decision_id}`")

    # --- Delete scenario ---
    st.markdown("### Delete entire scenario")
    st.write(
        "Removes this scenario, all its alternatives, criteria, measurements, "
        "preference sets, value functions, and every run."
    )
    scen_token = f"DELETE SCENARIO {scenario_id[:8]}"
    scen_ack = st.checkbox(
        "I understand scenario delete is permanent",
        value=False,
        key=f"ack_scen_{scenario_id}",
    )
    scen_typed = st.text_input(
        f"Type to confirm: `{scen_token}`",
        value="",
        key=f"type_scen_{scenario_id}",
    )
    scen_ok = scen_ack and scen_typed.strip() == scen_token

    if st.button("🗑 Delete scenario", disabled=not scen_ok, key=f"btn_del_scen_{scenario_id}"):
        res = deleter.delete_scenario(scenario_id)
        if res.ok:
            st.session_state["scenario_id"] = None
            st.session_state["preference_set_id"] = None
            st.session_state["last_run_id"] = None
            st.success(res.message)
            st.switch_page("pages/1_decision_setup.py")
        else:
            st.warning(res.message)

    st.markdown("---")

    # --- Delete decision ---
    st.markdown("### Delete entire decision")
    st.write(
        "Removes the decision and **all scenarios** that belong to it, including every run and result."
    )
    if decision_id:
        dec_token = f"DELETE DECISION {decision_id[:8]}"
        dec_ack = st.checkbox(
            "I understand decision delete is permanent",
            value=False,
            key=f"ack_dec_{decision_id}",
        )
        dec_typed = st.text_input(
            f"Type to confirm: `{dec_token}`",
            value="",
            key=f"type_dec_{decision_id}",
        )
        dec_ok = dec_ack and dec_typed.strip() == dec_token

        if st.button("🗑 Delete decision", disabled=not dec_ok, key=f"btn_del_dec_{decision_id}"):
            res = deleter.delete_decision(decision_id)
            if res.ok:
                st.session_state["decision_id"] = None
                st.session_state["scenario_id"] = None
                st.session_state["preference_set_id"] = None
                st.session_state["last_run_id"] = None
                st.success(res.message)
                st.switch_page("pages/1_decision_setup.py")
            else:
                st.warning(res.message)
    else:
        st.info("Decision ID not found for this scenario.")
