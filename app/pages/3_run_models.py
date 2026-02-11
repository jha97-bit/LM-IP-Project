import bootstrap

import streamlit as st
from sqlalchemy import text

from persistence.engine import get_engine
from services.scenario_service import ScenarioService
from services.topsis_service import TopsisService
from persistence.repositories.result_repo import ResultRepo
from persistence.repositories.run_repo import RunRepo

st.title("Step 3: Run Models")

engine = get_engine()
scenario_id = st.session_state.get("scenario_id")
user_name = st.session_state.get("user_name", "")

if not scenario_id:
    st.info("Go to Step 1 and select a Scenario first.")
    st.stop()

# Navigation
nav_left, nav_right = st.columns(2)
with nav_left:
    if st.button("Back: Step 2 (Data Input)"):
        st.switch_page("pages/2_data_input.py")
with nav_right:
    if st.button("Next: Step 4 (Results)"):
        st.switch_page("pages/4_results.py")

st.divider()

# Preference set dropdown
with engine.begin() as conn:
    prefs = conn.execute(
        text("""
            SELECT preference_set_id::text AS preference_set_id, name, type, status, created_at
            FROM preference_sets
            WHERE scenario_id = :sid
            ORDER BY created_at DESC
        """),
        {"sid": scenario_id},
    ).mappings().all()
prefs = [dict(p) for p in prefs]

if not prefs:
    st.warning("No preference sets found. Go to Step 2 and create one, then save weights.")
    st.stop()

pref_id = st.selectbox(
    "Preference set",
    options=[p["preference_set_id"] for p in prefs],
    format_func=lambda x: next(pp["name"] for pp in prefs if pp["preference_set_id"] == x),
)

model = st.selectbox("Model to run", options=["TOPSIS"], index=0)

scenario_service = ScenarioService(engine)
result_repo = ResultRepo(engine)
run_repo = RunRepo(engine)
topsis_service = TopsisService(engine)

# Load + validate
try:
    data = scenario_service.load(scenario_id, pref_id)
    ok, issues = scenario_service.validate(data)
except Exception as e:
    st.error(str(e))
    st.stop()

st.subheader("Validation")
if ok:
    st.success("Scenario is runnable.")
else:
    for msg in issues:
        st.error(msg)
    st.stop()

st.divider()

st.subheader("Run")
if st.button("Run and Save", type="primary"):
    if model == "TOPSIS":
        run_id = topsis_service.run_and_persist(
            scenario_id=scenario_id,
            preference_set_id=pref_id,
            executed_by=user_name,
            data=data,
        )
        st.session_state["last_run_id"] = run_id
        st.success(f"Run created: {run_id}")

        if st.button("View Results"):
             st.switch_page("pages/4_results.py")


        scores = result_repo.get_scores_with_names(run_id)
        st.subheader("Ranking")
        st.dataframe(scores, use_container_width=True)

st.divider()
st.subheader("Run History")
runs = run_repo.list_runs(scenario_id, limit=20)
if runs:
    st.dataframe(runs, use_container_width=True)
else:
    st.info("No runs yet.")
