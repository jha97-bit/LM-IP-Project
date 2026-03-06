import bootstrap

import streamlit as st
from persistence.engine import get_engine
from persistence.repositories.decision_repo import DecisionRepo
from persistence.repositories.scenario_repo import ScenarioRepo

st.title("Step 1: Decision and Scenario Setup")

engine = get_engine()
decision_repo = DecisionRepo(engine)
scenario_repo = ScenarioRepo(engine)

st.session_state.setdefault("decision_id", None)
st.session_state.setdefault("scenario_id", None)

# ----------------------------
# 1A) Decision
# ----------------------------
st.subheader("1A) Select or Create Decision")

decisions = decision_repo.list_decisions(limit=50) or []
decision_ids = [d["decision_id"] for d in decisions]
decision_id_to_title = {d["decision_id"]: d["title"] for d in decisions}

DEC_CREATE = "Create new…"
decision_options = [DEC_CREATE] + decision_ids

default_decision = st.session_state.get("decision_id") or (decision_ids[0] if decision_ids else DEC_CREATE)
if default_decision not in decision_options:
    default_decision = DEC_CREATE

picked_decision = st.multiselect(
    "Decision",
    options=decision_options,
    default=[default_decision],
    max_selections=1,
    format_func=lambda x: DEC_CREATE if x == DEC_CREATE else decision_id_to_title.get(x, x),
    key="decision_pick_step1",
)

selected_decision = picked_decision[0] if picked_decision else DEC_CREATE

if selected_decision == DEC_CREATE:
    title = st.text_input("Decision title", value="Admissions Selection")
    purpose = st.text_area("Purpose / context", value="Select best candidate using MCDA.", height=90)
    owner_team = st.text_input("Owner team (optional)", value="")

    if st.button("Create Decision", type="primary"):
        did = decision_repo.create_decision(title.strip(), purpose.strip(), owner_team.strip())
        st.session_state["decision_id"] = did
        st.session_state["scenario_id"] = None
        st.success(f"Decision created: {did}")
        st.rerun()
else:
    if st.session_state.get("decision_id") != selected_decision:
        st.session_state["decision_id"] = selected_decision
        st.session_state["scenario_id"] = None
    st.info(f"Selected decision: {selected_decision}")

st.divider()

# ----------------------------
# 1B) Scenario
# ----------------------------
st.subheader("1B) Select or Create Scenario")

if not st.session_state.get("decision_id"):
    st.warning("Select or create a Decision first.")
    st.stop()

scenarios = scenario_repo.list_scenarios(st.session_state["decision_id"], limit=100) or []
scenario_ids = [s["scenario_id"] for s in scenarios]
scenario_id_to_name = {s["scenario_id"]: s["name"] for s in scenarios}

SCEN_CREATE = "Create new…"
scenario_options = [SCEN_CREATE] + scenario_ids

default_scenario = st.session_state.get("scenario_id") or (scenario_ids[0] if scenario_ids else SCEN_CREATE)
if default_scenario not in scenario_options:
    default_scenario = SCEN_CREATE

picked_scenario = st.multiselect(
    "Scenario",
    options=scenario_options,
    default=[default_scenario],
    max_selections=1,
    format_func=lambda x: SCEN_CREATE if x == SCEN_CREATE else scenario_id_to_name.get(x, x),
    key=f"scenario_pick_step1_{st.session_state['decision_id']}",
)

selected_scenario = picked_scenario[0] if picked_scenario else SCEN_CREATE

if selected_scenario == SCEN_CREATE:
    sname = st.text_input("Scenario name", value="Base Case")
    sdesc = st.text_area("Scenario description (optional)", value="", height=90)
    created_by = st.session_state.get("user_name", "")

    if st.button("Create Scenario"):
        sid = scenario_repo.create_scenario(
            decision_id=st.session_state["decision_id"],
            name=sname.strip(),
            description=sdesc.strip(),
            created_by=created_by,
        )
        st.session_state["scenario_id"] = sid
        st.success(f"Scenario created: {sid}")
        st.rerun()
else:
    st.session_state["scenario_id"] = selected_scenario
    st.info(f"Selected scenario: {selected_scenario}")

st.divider()

col1, col2 = st.columns(2)
with col1:
    st.button("Back", disabled=True)
with col2:
    can_next = bool(st.session_state.get("scenario_id"))
    if st.button("Next: Go to Data Input", type="primary", disabled=not can_next):
        st.switch_page("pages/2_data_input.py")

st.caption("Decision holds the business problem. Scenario holds a version of inputs under that decision.")
