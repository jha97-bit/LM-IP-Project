# app/pages/7_report_builder.py
import bootstrap

from io import BytesIO
from typing import Dict, List, Optional

import pandas as pd
import streamlit as st
from sqlalchemy import text

from persistence.engine import get_engine
from persistence.repositories.measurement_repo import MeasurementRepo
from persistence.repositories.preference_repo import PreferenceRepo
from persistence.repositories.result_repo import ResultRepo
from persistence.repositories.topsis_read_repo import TopsisReadRepo
from services.report_export_service import ReportExportService


st.title("Step 7: Report Builder")

engine = get_engine()
meas_repo = MeasurementRepo(engine)
pref_repo = PreferenceRepo(engine)
result_repo = ResultRepo(engine)
topsis_read = TopsisReadRepo(engine)
export_svc = ReportExportService(engine)

st.session_state.setdefault("user_name", "")
st.session_state.setdefault("report_title", "MCDA Run Report")
st.session_state.setdefault("report_notes", "")

# Navigation
nav_left, nav_right = st.columns(2)
with nav_left:
    if st.button("Back: Step 5 (History)"):
        st.switch_page("pages/5_history.py")
with nav_right:
    st.button("Next", disabled=True)

st.divider()

# ----------------------------
# Helpers
# ----------------------------
def _single_pick_multiselect(label: str, options: List[str], default: Optional[str], fmt) -> str:
    if not options:
        return ""
    if default not in options:
        default = options[0]
    picked = st.multiselect(
        label,
        options=options,
        default=[default],
        max_selections=1,
        format_func=fmt,
        key=f"{label}_{hash(tuple(options))}",
    )
    return picked[0] if picked else default

def _format_float(x):
    try:
        if pd.isna(x):
            return ""
        return f"{float(x):.4f}"
    except Exception:
        return str(x)

def _make_inputs_table(matrix_df: pd.DataFrame, weights_map: Dict[str, float]) -> pd.DataFrame:
    crit_cols = list(matrix_df.columns)
    weights_row = {c: float(weights_map.get(c, 0.0)) for c in crit_cols}
    weights_df = pd.DataFrame([weights_row], index=["Weight"])
    combined_df = pd.concat([weights_df, matrix_df], axis=0)
    return combined_df

def _df_to_clean_display(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for c in out.columns:
        out[c] = out[c].map(_format_float)
    return out

def _styled_html_table(df_disp: pd.DataFrame, hover_header: Dict[str, str], hover_row: Dict[str, str]) -> str:
    cols = ["Alternative / Row"] + list(df_disp.columns)

    # header with tooltips
    thead = "<tr>" + "".join(
        [f"<th title='{st.session_state.get('_tt_tmp','')}'>{cols[0]}</th>"] +
        [f"<th title='{hover_header.get(c, '')}'>{c}</th>" for c in df_disp.columns]
    ) + "</tr>"

    tbody_rows = []
    for idx, row in df_disp.iterrows():
        idx_tt = hover_row.get(str(idx), "")
        tds = [f"<td class='idx' title='{idx_tt}'>{idx}</td>"]
        for c in df_disp.columns:
            tds.append(f"<td>{row[c]}</td>")
        tbody_rows.append("<tr>" + "".join(tds) + "</tr>")

    tbody = "".join(tbody_rows)

    return f"""
    <div class="mcda-panel">
      <div class="mcda-wrap">
        <table class="mcda-table">
          <thead>{thead}</thead>
          <tbody>{tbody}</tbody>
        </table>
      </div>
    </div>
    """

def _inject_table_css():
    st.markdown(
        """
        <style>
          .mcda-panel {
            display: flex;
            justify-content: flex-end;
            width: 100%;
          }
          .mcda-wrap {
            width: 100%;
            max-width: 1200px;
            overflow-x: auto;
            border: 1px solid rgba(0,0,0,0.12);
            border-radius: 12px;
            background: rgba(255,255,255,0.02);
          }
          table.mcda-table {
            border-collapse: separate;
            border-spacing: 0;
            width: 100%;
            min-width: 900px;
            font-size: 14px;
          }
          .mcda-table thead th {
            position: sticky;
            top: 0;
            background: rgba(250,250,250,0.95);
            backdrop-filter: blur(6px);
            z-index: 2;
            text-align: right;
            padding: 10px 12px;
            border-bottom: 1px solid rgba(0,0,0,0.12);
            font-weight: 600;
            white-space: nowrap;
          }
          .mcda-table thead th:first-child {
            text-align: left;
          }
          .mcda-table tbody td {
            padding: 10px 12px;
            border-bottom: 1px solid rgba(0,0,0,0.08);
            text-align: right;
            white-space: nowrap;
          }
          .mcda-table tbody td.idx {
            text-align: left;
            font-weight: 600;
          }
          .mcda-table tbody tr:nth-child(odd) td {
            background: rgba(0,0,0,0.015);
          }
          .mcda-table tbody tr:first-child td {
            background: rgba(255, 235, 59, 0.12);
            font-weight: 700;
          }
        </style>
        """,
        unsafe_allow_html=True,
    )

def _load_decisions() -> List[dict]:
    with engine.begin() as conn:
        rows = conn.execute(
            text("""
                SELECT decision_id::text AS decision_id, title, purpose, owner_team, created_at
                FROM decisions
                ORDER BY created_at DESC
                LIMIT 200
            """)
        ).mappings().all()
    return [dict(r) for r in rows]

def _load_scenarios(decision_id: str) -> List[dict]:
    with engine.begin() as conn:
        rows = conn.execute(
            text("""
                SELECT scenario_id::text AS scenario_id, name, description, created_at, created_by
                FROM scenarios
                WHERE decision_id = :did
                ORDER BY created_at DESC
                LIMIT 300
            """),
            {"did": decision_id},
        ).mappings().all()
    return [dict(r) for r in rows]

def _load_prefs(scenario_id: str) -> List[dict]:
    with engine.begin() as conn:
        rows = conn.execute(
            text("""
                SELECT preference_set_id::text AS preference_set_id, name, type, status, created_at
                FROM preference_sets
                WHERE scenario_id = :sid
                ORDER BY created_at DESC
                LIMIT 300
            """),
            {"sid": scenario_id},
        ).mappings().all()
    return [dict(r) for r in rows]

def _load_runs(scenario_id: str, pref_id: str) -> List[dict]:
    with engine.begin() as conn:
        rows = conn.execute(
            text("""
                SELECT run_id::text AS run_id, executed_at, executed_by, method, engine_version, run_label
                FROM runs
                WHERE scenario_id = :sid
                  AND preference_set_id = :pid
                ORDER BY executed_at DESC
                LIMIT 500
            """),
            {"sid": scenario_id, "pid": pref_id},
        ).mappings().all()
    return [dict(r) for r in rows]

def _load_criteria_meta(scenario_id: str) -> Dict[str, dict]:
    with engine.begin() as conn:
        rows = conn.execute(
            text("""
                SELECT name, direction, scale_type, unit, description
                FROM criteria
                WHERE scenario_id = :sid
            """),
            {"sid": scenario_id},
        ).mappings().all()
    meta = {}
    for r in rows:
        meta[str(r["name"])] = dict(r)
    return meta

def _load_alt_meta(scenario_id: str) -> Dict[str, dict]:
    with engine.begin() as conn:
        rows = conn.execute(
            text("""
                SELECT name
                FROM alternatives
                WHERE scenario_id = :sid
                ORDER BY created_at ASC
            """),
            {"sid": scenario_id},
        ).mappings().all()
    meta = {}
    for r in rows:
        meta[str(r["name"])] = dict(r)
    return meta

# ----------------------------
# Pick Decision, Scenario, Preference set
# ----------------------------
st.subheader("Pick inputs")

decisions = _load_decisions()
if not decisions:
    st.warning("No decisions found. Create one in Step 1.")
    st.stop()

decision_ids = [d["decision_id"] for d in decisions]
decision_id_to_title = {d["decision_id"]: d["title"] for d in decisions}

default_decision = st.session_state.get("decision_id") or decision_ids[0]
picked_decision_id = _single_pick_multiselect(
    "Decision",
    decision_ids,
    default_decision,
    fmt=lambda x: decision_id_to_title.get(x, x),
)
st.session_state["decision_id"] = picked_decision_id

scenarios = _load_scenarios(picked_decision_id)
if not scenarios:
    st.warning("No scenarios under this decision. Create one in Step 1.")
    st.stop()

scenario_ids = [s["scenario_id"] for s in scenarios]
scenario_id_to_name = {s["scenario_id"]: s["name"] for s in scenarios}

default_scenario = st.session_state.get("scenario_id") or scenario_ids[0]
picked_scenario_id = _single_pick_multiselect(
    "Scenario",
    scenario_ids,
    default_scenario,
    fmt=lambda x: scenario_id_to_name.get(x, x),
)
st.session_state["scenario_id"] = picked_scenario_id

prefs = _load_prefs(picked_scenario_id)
if not prefs:
    st.warning("No preference sets found for this scenario. Create one in Step 2.")
    st.stop()

pref_ids = [p["preference_set_id"] for p in prefs]
pref_id_to_name = {p["preference_set_id"]: p["name"] for p in prefs}

default_pref = st.session_state.get("preference_set_id") or pref_ids[0]
picked_pref_id = _single_pick_multiselect(
    "Preference set",
    pref_ids,
    default_pref,
    fmt=lambda x: pref_id_to_name.get(x, x),
)
st.session_state["preference_set_id"] = picked_pref_id

st.divider()

# ----------------------------
# Pick runs (up to 5)
# ----------------------------
runs = _load_runs(picked_scenario_id, picked_pref_id)
if not runs:
    st.warning("No runs found for this scenario + preference set. Run TOPSIS in Step 3.")
    st.stop()

def _run_label(r: dict) -> str:
    lbl = (r.get("run_label") or "").strip()
    by = (r.get("executed_by") or "").strip()
    by_part = f" by {by}" if by else ""
    if lbl:
        return f"{lbl} | {r['executed_at']}{by_part}"
    return f"{r['executed_at']}{by_part} | {r['run_id'][:8]}…"

run_ids = [r["run_id"] for r in runs]
run_id_to_row = {r["run_id"]: r for r in runs}
default_run = st.session_state.get("last_run_id") if st.session_state.get("last_run_id") in run_ids else run_ids[0]

picked_runs = st.multiselect(
    "Runs to include in report (2 to 5 recommended for comparison)",
    options=run_ids,
    default=[default_run],
    max_selections=5,
    format_func=lambda rid: _run_label(run_id_to_row[rid]),
    key=f"report_runs_{picked_scenario_id}_{picked_pref_id}",
)

if not picked_runs:
    st.info("Pick at least 1 run.")
    st.stop()

st.session_state["last_run_id"] = picked_runs[0]

st.divider()

# ----------------------------
# Report editing
# ----------------------------
st.subheader("Report content")

colA, colB = st.columns([3, 2])
with colA:
    st.session_state["report_title"] = st.text_input("Report title", value=st.session_state["report_title"])
with colB:
    st.session_state["user_name"] = st.text_input("Author", value=st.session_state.get("user_name", ""))

st.session_state["report_notes"] = st.text_area(
    "Notes (editable narrative that will appear in the export)",
    value=st.session_state["report_notes"],
    height=180,
)

st.divider()

# ----------------------------
# Load inputs preview (matrix + weights) with hover tooltips
# ----------------------------
st.subheader("Inputs used for results")

matrix_df = meas_repo.load_matrix_ui(picked_scenario_id)
weights_map = pref_repo.load_weights_by_criterion_name(picked_pref_id)

if matrix_df is None or matrix_df.empty:
    st.info("No performance matrix found. Fill Step 2 and save Matrix + Weights.")
    st.stop()

combined_df = _make_inputs_table(matrix_df, weights_map)
combined_disp = _df_to_clean_display(combined_df)

criteria_meta = _load_criteria_meta(picked_scenario_id)
alt_meta = _load_alt_meta(picked_scenario_id)

hover_header = {}
for c in matrix_df.columns:
    m = criteria_meta.get(c, {})
    bits = []
    if m.get("direction"):
        bits.append(f"direction: {m['direction']}")
    if m.get("scale_type"):
        bits.append(f"scale: {m['scale_type']}")
    if m.get("unit"):
        bits.append(f"unit: {m['unit']}")
    if m.get("description"):
        bits.append(f"description: {m['description']}")
    hover_header[c] = " | ".join(bits)

hover_row = {}
for idx in combined_disp.index:
    if str(idx) == "Weight":
        hover_row[str(idx)] = "Weights for each criterion"
    else:
        hover_row[str(idx)] = "Alternative"

_inject_table_css()
st.markdown(_styled_html_table(combined_disp, hover_header, hover_row), unsafe_allow_html=True)

st.download_button(
    "Download Matrix + Weights CSV",
    data=combined_df.to_csv().encode("utf-8"),
    file_name=f"matrix_with_weights_{picked_runs[0]}.csv",
    mime="text/csv",
)

st.divider()

# ----------------------------
# Report preview (scores and charts)
# ----------------------------
st.subheader("Results preview")

preview_tabs = st.tabs(["Ranking", "Comparison"])

with preview_tabs[0]:
    st.caption("Ranking for the first selected run")
    run0 = picked_runs[0]
    scores0 = pd.DataFrame(result_repo.get_scores_with_names(run0))
    if scores0.empty:
        st.info("No results found for the selected run.")
    else:
        st.dataframe(scores0, width="stretch")

with preview_tabs[1]:
    if len(picked_runs) < 2:
        st.info("Pick at least 2 runs to enable comparison preview.")
    else:
        st.caption("Scores compared across selected runs")
        comp_rows = []
        for rid in picked_runs:
            df = pd.DataFrame(result_repo.get_scores_with_names(rid))
            if df.empty:
                continue
            df = df[["alternative_name", "score", "rank"]].copy()
            df["run_id"] = rid
            df["run_label"] = _run_label(run_id_to_row[rid])
            comp_rows.append(df)

        if not comp_rows:
            st.info("No comparable results found.")
        else:
            comp = pd.concat(comp_rows, axis=0, ignore_index=True)
            st.dataframe(comp, width="stretch")

st.divider()

# ----------------------------
# Export
# ----------------------------
st.subheader("Export")

export_col1, export_col2 = st.columns([1, 3])
with export_col1:
    do_export = st.button("Export DOCX", type="primary")
with export_col2:
    st.caption("Export builds a Word document with report title, metadata, notes, inputs table, rankings per run, and comparison charts.")

if do_export:
    payload = {
        "report_title": st.session_state["report_title"],
        "author": st.session_state.get("user_name", ""),
        "notes": st.session_state.get("report_notes", ""),
        "decision_id": picked_decision_id,
        "decision_title": decision_id_to_title.get(picked_decision_id, ""),
        "scenario_id": picked_scenario_id,
        "scenario_name": scenario_id_to_name.get(picked_scenario_id, ""),
        "preference_set_id": picked_pref_id,
        "preference_set_name": pref_id_to_name.get(picked_pref_id, ""),
        "runs": [
            {
                **run_id_to_row[rid],
                "run_id": rid,
                "run_label_display": _run_label(run_id_to_row[rid]),
            }
            for rid in picked_runs
        ],
        "inputs_table": combined_df,  # real numeric table
        "criteria_meta": criteria_meta,
    }

    docx_bytes = export_svc.build_docx_report(payload)
    st.download_button(
        "Download report.docx",
        data=docx_bytes,
        file_name="mcda_report.docx",
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
