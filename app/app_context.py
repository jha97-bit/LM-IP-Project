import streamlit as st

from persistence.engine import get_engine
from persistence.repositories.scenario_repo import ScenarioRepo

FLOW_TOPSIS = [
    ("setup", "Decision Setup", "pages/1_decision_setup.py", "🧭"),
    ("data", "Data Input", "pages/2_data_input.py", "📊"),
    ("run_model", "Run Model", "pages/3_run_models.py", "▶️"),
    ("results", "Results", "pages/4_results.py", "🏆"),
    ("sensitivity", "Sensitivity", "pages/5_sensitivity.py", "🧪"),
    ("report", "Report Builder", "pages/6_report_builder.py", "📝"),
    ("history", "History", "pages/7_history.py", "🕘"),
]

FLOW_VFT = [
    ("setup", "Decision Setup", "pages/1_decision_setup.py", "🧭"),
    ("data", "Data Input", "pages/2_data_input.py", "📊"),
    ("value_functions", "Value Functions", "pages/3b_vft_value_functions.py", "📈"),
    ("run_model", "Run Model", "pages/3_run_models.py", "▶️"),
    ("results", "Results", "pages/4_results.py", "🏆"),
    ("sensitivity", "Sensitivity", "pages/5_sensitivity.py", "🧪"),
    ("report", "Report Builder", "pages/6_report_builder.py", "📝"),
    ("history", "History", "pages/7_history.py", "🕘"),
]

FLOW_AHP = [
    ("setup", "Decision Setup", "pages/1_decision_setup.py", "🧭"),
    ("data", "Data Input", "pages/2_data_input.py", "📊"),
    ("run_model", "Run Model", "pages/3_run_models.py", "▶️"),
    ("results", "Results", "pages/4_results.py", "🏆"),
    ("sensitivity", "Sensitivity", "pages/5_sensitivity.py", "🧪"),
    ("report", "Report Builder", "pages/6_report_builder.py", "📝"),
    ("history", "History", "pages/7_history.py", "🕘"),
]


def sync_method_from_scenario(scenario_id: str | None = None):
    sid = scenario_id or st.session_state.get("scenario_id")
    if not sid:
        return None

    repo = ScenarioRepo(get_engine())
    scenario = repo.get_scenario(sid)
    if not scenario:
        return None

    st.session_state["scenario_id"] = scenario["scenario_id"]
    st.session_state["decision_id"] = scenario["decision_id"]
    st.session_state["method_choice"] = scenario.get("method_type")
    return scenario


def get_active_method() -> str | None:
    method = st.session_state.get("method_choice")
    if method:
        return method

    scenario = sync_method_from_scenario()
    return scenario.get("method_type") if scenario else None


def get_active_flow():
    m = get_active_method()
    if m == "vft":
        return FLOW_VFT
    if m == "ahp":
        return FLOW_AHP
    return FLOW_TOPSIS


def get_allowed_page_paths():
    return {item[2] for item in get_active_flow()}


def guard_page(page_path: str, require_scenario: bool = True):
    if require_scenario and not st.session_state.get("scenario_id"):
        st.switch_page("pages/1_decision_setup.py")

    if st.session_state.get("scenario_id"):
        sync_method_from_scenario()

    method = st.session_state.get("method_choice")
    if require_scenario and not method:
        st.switch_page("pages/1_decision_setup.py")

    if method and page_path not in get_allowed_page_paths():
        first_valid = get_active_flow()[0][2]
        st.switch_page(first_valid)


def set_scenario_context(scenario_id: str):
    scenario = sync_method_from_scenario(scenario_id)
    return scenario
