# app/pages/5_history.py
import bootstrap  # noqa: F401

import streamlit as st
import pandas as pd
from sqlalchemy import text

from persistence.engine import get_engine
from services.delete_service import DeleteService

st.title("Step 5: History and Logs")

engine = get_engine()
deleter = DeleteService(engine)

scenario_id = st.session_state.get("scenario_id")
if not scenario_id:
    st.info("Go to Step 1 and select a Scenario first.")
    st.stop()

# Navigation
nav_left, nav_right = st.columns(2)
with nav_left:
    if st.button("Back: Step 4 (Results)"):
        st.switch_page("pages/4_results.py")
with nav_right:
    if st.button("Next: Step 6 (Compare)"):
        st.switch_page("pages/6_compare.py")


st.divider()

# ----------------------------
# Fetch current decision_id (for danger zone)
# ----------------------------
with engine.begin() as conn:
    row = conn.execute(
        text("""
            SELECT decision_id::text AS decision_id
            FROM scenarios
            WHERE scenario_id = :sid
        """),
        {"sid": scenario_id},
    ).mappings().first()

decision_id = row["decision_id"] if row else None

# ----------------------------
# Pref map (names)
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
# Runs table (only fields you want)
# ----------------------------
st.subheader("Run History (Current Scenario)")

# If you later add run_label column, this query will still work
# by probing if run_label exists.
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
    st.info("No runs yet. Go to Step 3 to run TOPSIS.")
    st.stop()

runs_df = pd.DataFrame(runs)
runs_df["preference_set_name"] = runs_df["preference_set_id"].map(lambda x: pref_id_to_name.get(x, x))

# Force display columns in the exact order you asked
display_cols = ["executed_at", "method", "preference_set_name", "executed_by", "run_label", "run_id"]
runs_df = runs_df[display_cols]

st.dataframe(runs_df, width="stretch")

st.download_button(
    "Download History CSV",
    data=runs_df.to_csv(index=False).encode("utf-8"),
    file_name="run_history.csv",
    mime="text/csv",
)

st.divider()

# ----------------------------
# Select a run for actions
# ----------------------------
st.subheader("Open or Manage a Run")

run_options = runs_df["run_id"].tolist()

def _label_from_run_id(rid: str) -> str:
    r = next(rr for rr in runs if rr["run_id"] == rid)
    pref_name = pref_id_to_name.get(r["preference_set_id"], r["preference_set_id"][:8] + "…")
    base = f"{r['executed_at']} | {str(r['method']).upper()} | {pref_name}"
    if r.get("executed_by"):
        base += f" | {r['executed_by']}"
    if r.get("run_label"):
        base = f"{r['run_label']} | " + base
    return base

picked = st.multiselect(
    "Pick a run",
    options=run_options,
    max_selections=1,
    default=[st.session_state.get("last_run_id")] if st.session_state.get("last_run_id") in run_options else [run_options[0]],
    format_func=_label_from_run_id,
    key=f"history_run_pick_{scenario_id}",
)
run_id = picked[0] if picked else run_options[0]

# Load run metadata to enable "load build"
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

if not meta:
    st.error("Run not found.")
    st.stop()

btn1, btn2, btn3 = st.columns([1, 1, 2])

with btn1:
    if st.button("Go to Results"):
        st.session_state["scenario_id"] = meta["scenario_id"]
        st.session_state["preference_set_id"] = meta["preference_set_id"]
        st.session_state["last_run_id"] = meta["run_id"]
        st.switch_page("pages/4_results.py")

with btn2:
    if st.button("Load this build"):
        # This makes your app jump back with all context preselected
        st.session_state["scenario_id"] = meta["scenario_id"]
        st.session_state["preference_set_id"] = meta["preference_set_id"]
        st.session_state["last_run_id"] = meta["run_id"]
        st.success("Loaded build into session. You can go to Step 4 to view results or Step 3 to rerun.")

with btn3:
    st.caption("Tip: “Load this build” sets Scenario + Preference Set + Run for fast return to your exact results.")

st.divider()

# ----------------------------
# Delete run (double confirmation)
# ----------------------------
st.subheader("Delete Run")

token = f"DELETE {run_id[:8]}"
st.warning("This deletes the run and all generated TOPSIS artifacts for that run. It does not delete your scenario inputs.")

ack = st.checkbox("I understand this is permanent", value=False, key=f"ack_run_{run_id}")
typed = st.text_input(f"Type to confirm: {token}", value="", key=f"type_run_{run_id}")

can_delete = ack and typed.strip() == token

if st.button("Delete this run", type="primary", disabled=not can_delete, key=f"btn_del_run_{run_id}"):
    res = deleter.delete_run(run_id)
    if res.ok:
        # Clear if you deleted the selected run
        if st.session_state.get("last_run_id") == run_id:
            st.session_state["last_run_id"] = None
        st.success(res.message)
        st.rerun()
    else:
        st.error(res.message)

# ----------------------------
# Danger Zone
# ----------------------------
with st.expander("Danger zone: delete scenario or decision", expanded=False):
    st.error("These actions delete inputs and history. Use only if you really want to wipe data.")

    if decision_id:
        st.caption(f"Current scenario_id: {scenario_id}")
        st.caption(f"Current decision_id: {decision_id}")

    st.markdown("### Delete entire scenario")
    scen_token = f"DELETE SCENARIO {scenario_id[:8]}"
    scen_ack = st.checkbox("I understand scenario delete is permanent", value=False, key=f"ack_scen_{scenario_id}")
    scen_typed = st.text_input(f"Type to confirm: {scen_token}", value="", key=f"type_scen_{scenario_id}")
    scen_ok = scen_ack and scen_typed.strip() == scen_token

    if st.button("Delete scenario", disabled=not scen_ok, key=f"btn_del_scen_{scenario_id}"):
        res = deleter.delete_scenario(scenario_id)
        if res.ok:
            st.session_state["scenario_id"] = None
            st.session_state["preference_set_id"] = None
            st.session_state["last_run_id"] = None
            st.success(res.message)
            st.switch_page("pages/1_decision_setup.py")
        else:
            st.error(res.message)

    st.markdown("### Delete entire decision")
    if decision_id:
        dec_token = f"DELETE DECISION {decision_id[:8]}"
        dec_ack = st.checkbox("I understand decision delete is permanent", value=False, key=f"ack_dec_{decision_id}")
        dec_typed = st.text_input(f"Type to confirm: {dec_token}", value="", key=f"type_dec_{decision_id}")
        dec_ok = dec_ack and dec_typed.strip() == dec_token

        if st.button("Delete decision", disabled=not dec_ok, key=f"btn_del_dec_{decision_id}"):
            res = deleter.delete_decision(decision_id)
            if res.ok:
                st.session_state["decision_id"] = None
                st.session_state["scenario_id"] = None
                st.session_state["preference_set_id"] = None
                st.session_state["last_run_id"] = None
                st.success(res.message)
                st.switch_page("pages/1_decision_setup.py")
            else:
                st.error(res.message)
    else:
        st.info("Decision id not found for this scenario.")
