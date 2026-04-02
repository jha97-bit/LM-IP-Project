import bootstrap  # noqa: F401

import streamlit as st
from app.ui_theme import apply_theme, BLUE_SCALE, TEAL_SCALE, BLUE_TEAL_SCALE, DISCRETE_PALETTE, section_header
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.app_context import set_scenario_context
from app.sidebar_nav import render_sidebar
from persistence.engine import get_engine
from persistence.repositories.decision_repo import DecisionRepo
from persistence.repositories.scenario_repo import ScenarioRepo
from services.scenario_share_service import ScenarioShareService

st.set_page_config(page_title="MCDA — Decision Setup", layout="wide")
apply_theme()
st.title("Step 1: Decision & Scenario Setup")
section_header("Decision & Scenario Setup", variant="gradient")
st.markdown(
    """
    <style>
    /* Compact vertical rhythm for Step 1 */
    div[data-testid="stExpander"] { margin-top: 6px !important; margin-bottom: 8px !important; }
    div[data-testid="stExpander"] + div { margin-top: 0 !important; }
    h2, h3 { margin-bottom: 0.35rem !important; }
    p { margin-bottom: 0.45rem !important; }
    </style>
    """,
    unsafe_allow_html=True,
)

engine = get_engine()
decision_repo = DecisionRepo(engine)
scenario_repo = ScenarioRepo(engine)
share_svc = ScenarioShareService(engine)

st.session_state.setdefault("decision_id", None)
st.session_state.setdefault("scenario_id", None)
st.session_state.setdefault("method_choice", None)
st.session_state.setdefault("user_name", "")

render_sidebar("pages/1_decision_setup.py")

user_name = st.session_state.get("user_name", "")

nav_col1, nav_col2 = st.columns([1, 1])
with nav_col1:
    if st.button("← Back to Home", key="nav_back_top"):
        st.switch_page("streamlit_app.py")
with nav_col2:
    can_next = bool(st.session_state.get("scenario_id")) and bool(st.session_state.get("method_choice"))
    if st.button("Next: Data Input →", type="primary", disabled=not can_next, key="nav_next_top"):
        st.switch_page("pages/2_data_input.py")

st.caption("Set the business decision context, then choose or create a scenario.")
st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)

# ─── 1A: Decision ──────────────────────────────────────────────────────────
section_header("1A. Select or Create a Decision", variant="accent")
st.caption("A Decision is the top-level business problem you are solving.")

decisions = decision_repo.list_decisions(limit=100) or []
decision_ids = [d["decision_id"] for d in decisions]
decision_id_to_title = {d["decision_id"]: d["title"] for d in decisions}

DEC_CREATE = "── Create new… ──"
decision_options = [DEC_CREATE] + decision_ids
default_decision = st.session_state.get("decision_id") or (decision_ids[0] if decision_ids else DEC_CREATE)
if default_decision not in decision_options:
    default_decision = DEC_CREATE

# Use selectbox (not multiselect @ max_selections=1) — multiselect shows a broken dark empty dropdown when at limit.
_dec_idx = decision_options.index(default_decision) if default_decision in decision_options else 0
selected_decision = st.selectbox(
    "Decision",
    options=decision_options,
    index=_dec_idx,
    format_func=lambda x: DEC_CREATE if x == DEC_CREATE else f"{decision_id_to_title.get(x, x)} ({x[:8]}…)",
    key="decision_pick_step1",
)

if selected_decision == DEC_CREATE:
    c1, c2 = st.columns(2)
    with c1:
        title = st.text_input("Decision title *", placeholder="e.g. Supplier Selection 2024")
        owner_team = st.text_input("Owner team (optional)", placeholder="e.g. Procurement")
    with c2:
        purpose = st.text_area("Purpose / context", height=90, placeholder="Briefly describe why this decision is being made.")
    if st.button("Create Decision", type="primary", disabled=not (title or "").strip(), key="btn_create_decision"):
        did = decision_repo.create_decision(title.strip(), (purpose or "").strip(), (owner_team or "").strip())
        st.session_state["decision_id"] = did
        st.session_state["scenario_id"] = None
        st.session_state["method_choice"] = None
        st.toast("✅ Decision created!", icon="🎉")
        st.rerun()
else:
    if st.session_state.get("decision_id") != selected_decision:
        st.session_state["decision_id"] = selected_decision
        st.session_state["scenario_id"] = None
        st.session_state["method_choice"] = None
        st.rerun()
    st.info(f"📋 Selected: **{decision_id_to_title.get(selected_decision, selected_decision)}**")

st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

# ─── Scenario Import — between Decision and Scenario ───────────────────────
with st.expander("Import a colleague's scenario (.mcda file)", expanded=False):
    st.info(
        "Upload a .mcda file (exported from Step 7 — History) to load a full scenario "
        "into your database. You can rename it before confirming import."
    )
    dec_id_for_import = st.session_state.get("decision_id")
    if not dec_id_for_import:
        st.warning("Select or create a Decision above before importing.")
    else:
        uploaded = st.file_uploader("Upload .mcda file", type=["mcda"], key="scenario_uploader")
        if uploaded:
            import_rename = st.text_input(
                "Rename imported scenario (optional — leave blank to keep original name)",
                key="import_rename_field",
            )
            c_imp1, c_imp2 = st.columns([1, 3])
            with c_imp1:
                do_import = st.button("Import Scenario", type="primary", key="btn_import_scenario")
            with c_imp2:
                st.caption(f"File: {uploaded.name} · {uploaded.size:,} bytes")
            if do_import:
                try:
                    file_bytes = uploaded.read()
                    result = share_svc.import_scenario(file_bytes, imported_by=user_name)
                    new_name = (import_rename or "").strip()
                    if new_name:
                        with engine.begin() as conn:
                            conn.execute(
                                text("UPDATE scenarios SET name=:name WHERE scenario_id=:sid"),
                                {"name": new_name, "sid": result["scenario_id"]},
                            )
                    st.session_state["decision_id"] = result["decision_id"]
                    st.session_state["scenario_id"] = result["scenario_id"]
                    set_scenario_context(result["scenario_id"])
                    st.toast(f"Imported: {new_name or result.get('scenario_name', '')}", icon="✅")
                    st.rerun()
                except Exception as e:
                    st.warning(f"Import failed: {e}")

st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)

# ─── 1B: Scenario ───────────────────────────────────────────────────────────
section_header("1B. Select or Create a Scenario", variant="accent")
st.caption("A Scenario is one versioned configuration of inputs under a decision.")

if not st.session_state.get("decision_id"):
    st.warning("Complete step 1A first — select or create a Decision.")
    st.stop()

scenarios = scenario_repo.list_scenarios(st.session_state["decision_id"], limit=200) or []
scenario_ids = [s["scenario_id"] for s in scenarios]
scenario_id_to_meta = {
    s["scenario_id"]: {
        "name": s["name"],
        "method_type": s.get("method_type", "topsis"),
        "description": s.get("description", ""),
    }
    for s in scenarios
}

SCEN_CREATE = "── Create new… ──"
scenario_options = [SCEN_CREATE] + scenario_ids
default_scenario = st.session_state.get("scenario_id") or (scenario_ids[0] if scenario_ids else SCEN_CREATE)
if default_scenario not in scenario_options:
    default_scenario = SCEN_CREATE

_scen_idx = scenario_options.index(default_scenario) if default_scenario in scenario_options else 0
selected_scenario = st.selectbox(
    "Scenario",
    options=scenario_options,
    index=_scen_idx,
    format_func=lambda x: (
        SCEN_CREATE if x == SCEN_CREATE else f"{scenario_id_to_meta[x]['name']} [{scenario_id_to_meta[x]['method_type'].upper()}] ({x[:8]}…)"
    ),
    key=f"scenario_pick_step1_{st.session_state['decision_id']}",
)

creating_new_scenario = selected_scenario == SCEN_CREATE

# ─── Method Selection ───────────────────────────────────────────────────────
section_header("Analysis Method", variant="sub")

locked_method = None
if not creating_new_scenario and selected_scenario in scenario_id_to_meta:
    locked_method = scenario_id_to_meta[selected_scenario]["method_type"]
    st.session_state["method_choice"] = locked_method

current_method = locked_method or st.session_state.get("method_choice") or "topsis"

METHOD_LABELS = {
    "topsis": "TOPSIS",
    "vft": "VFT — Value Focus Thinking",
    "ahp": "Legacy (not supported — create a new scenario)",
}

method_col1, method_col2 = st.columns(2, gap="large")
with method_col1:
    if st.button(
        "TOPSIS",
        type="primary" if current_method == "topsis" else "secondary",
        use_container_width=True,
        disabled=bool(locked_method),
        key="method_btn_topsis",
    ):
        st.session_state["method_choice"] = "topsis"
        st.rerun()
    st.caption("Distance-based ranking from ideal and anti-ideal solutions.")

with method_col2:
    if st.button(
        "VFT",
        type="primary" if current_method == "vft" else "secondary",
        use_container_width=True,
        disabled=bool(locked_method),
        key="method_btn_vft",
    ):
        st.session_state["method_choice"] = "vft"
        st.rerun()
    st.caption("Utility-based scoring with custom value functions per criterion.")

method_choice = st.session_state.get("method_choice")
if locked_method == "ahp":
    st.warning(
        "This scenario is labeled **AHP**, which is no longer supported in the app. "
        "Create a **new scenario** and choose **TOPSIS** or **VFT** to continue."
    )
elif locked_method:
    st.info(
        f"This scenario is locked to **{METHOD_LABELS.get(locked_method, locked_method.upper())}**. "
        "Create a new scenario if you want to use a different method."
    )
elif not method_choice:
    st.info("Select an analysis method for the new scenario.")
else:
    st.success(f"Method selected: **{METHOD_LABELS.get(method_choice, method_choice.upper())}**")

st.divider()

if creating_new_scenario:
    sc1, sc2 = st.columns(2)
    with sc1:
        sname = st.text_input("Scenario name *", placeholder="e.g. Base Case")
    with sc2:
        sdesc = st.text_area("Description (optional)", height=90, placeholder="What varies in this scenario?")

    can_create_scenario = bool((sname or "").strip()) and bool(st.session_state.get("method_choice"))
    if st.button("Create Scenario", type="primary", disabled=not can_create_scenario, key="btn_create_scenario"):
        scen_name_clean = sname.strip()
        try:
            sid = scenario_repo.create_scenario(
                decision_id=st.session_state["decision_id"],
                name=scen_name_clean,
                method_type=st.session_state["method_choice"],
                description=(sdesc or "").strip(),
                created_by=user_name,
            )
            st.session_state["scenario_id"] = sid
            set_scenario_context(sid)
            st.toast(f"✅ Scenario '{scen_name_clean}' created!", icon="📂")
            st.rerun()
        except IntegrityError:
            # Unique constraint: (decision_id, name). Select existing scenario instead of crashing.
            with engine.begin() as conn:
                row = conn.execute(
                    text(
                        """
                        SELECT scenario_id::text AS scenario_id, method_type
                        FROM scenarios
                        WHERE decision_id = :did AND name = :name
                        ORDER BY created_at DESC
                        LIMIT 1
                        """
                    ),
                    {"did": st.session_state["decision_id"], "name": scen_name_clean},
                ).mappings().first()
            if row:
                sid = str(row["scenario_id"])
                st.session_state["scenario_id"] = sid
                st.session_state["method_choice"] = row.get("method_type") or st.session_state.get("method_choice")
                set_scenario_context(sid)
                st.warning(
                    f"A scenario named **{scen_name_clean}** already exists for this decision. "
                    "Selected the existing scenario instead."
                )
                st.rerun()
            raise
else:
    st.session_state["scenario_id"] = selected_scenario
    scenario_meta = scenario_id_to_meta.get(selected_scenario, {})
    scen_name = scenario_meta.get("name", selected_scenario)
    set_scenario_context(selected_scenario)
    st.info(f"📂 Selected: **{scen_name}**")

    with st.expander("✏️ Rename this scenario", expanded=False):
        new_scen_name = st.text_input("New name", value=scen_name, key=f"rename_scen_{selected_scenario}")
        if st.button(
            "Rename Scenario",
            key=f"btn_rename_{selected_scenario}",
            disabled=not (new_scen_name or "").strip(),
        ):
            with engine.begin() as conn:
                conn.execute(
                    text("UPDATE scenarios SET name=:name WHERE scenario_id=:sid"),
                    {"name": new_scen_name.strip(), "sid": selected_scenario},
                )
            st.toast(f"✅ Renamed to '{new_scen_name.strip()}'", icon="✏️")
            st.rerun()

# ─── Summary ────────────────────────────────────────────────────────────────
if st.session_state.get("scenario_id"):
    st.divider()
    s1, s2, s3 = st.columns(3)
    with s1:
        _mc = st.session_state.get("method_choice") or "topsis"
        st.metric("Method", METHOD_LABELS.get(_mc, _mc.upper()))
    with s2:
        st.metric("Decision", decision_id_to_title.get(st.session_state.get("decision_id", ""), "—")[:30])
    with s3:
        current_scenario_name = scenario_id_to_meta.get(st.session_state.get("scenario_id", ""), {}).get("name", "—")
        st.metric("Scenario", current_scenario_name[:30])

    col_prev, col_next = st.columns(2)
    with col_prev:
        if st.button("← Back to Home", key="nav_back_bottom"):
            st.switch_page("streamlit_app.py")
    with col_next:
        _blocked = st.session_state.get("method_choice") == "ahp"
        if st.button(
            "Next: Data Input →",
            type="primary",
            key="nav_next_bottom",
            disabled=_blocked,
        ):
            st.switch_page("pages/2_data_input.py")
