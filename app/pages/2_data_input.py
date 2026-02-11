import bootstrap

import numpy as np
import pandas as pd
import streamlit as st
from sqlalchemy import text

from persistence.engine import get_engine
from persistence.repositories.alternative_repo import AlternativeRepo
from persistence.repositories.criterion_repo import CriterionRepo
from persistence.repositories.measurement_repo import MeasurementRepo
from persistence.repositories.preference_repo import PreferenceRepo


st.title("Step 2: Data Input")

engine = get_engine()
alt_repo = AlternativeRepo(engine)
crit_repo = CriterionRepo(engine)
meas_repo = MeasurementRepo(engine)
pref_repo = PreferenceRepo(engine)

scenario_id = st.session_state.get("scenario_id")
user_name = st.session_state.get("user_name", "")

if not scenario_id:
    st.info("Go to Step 1 and create or select a Scenario first.")
    st.stop()

st.session_state.setdefault("preference_set_id", None)
st.session_state.setdefault("data_ready", False)

# ----------------------------
# Navigation
# ----------------------------
nav_left, nav_right = st.columns(2)

with nav_left:
    if st.button("Back: Step 1 (Decision and Scenario)"):
        st.switch_page("pages/1_decision_setup.py")

with nav_right:
    can_next = bool(st.session_state.get("data_ready"))
    if st.button("Next: Step 3 (Run Models)", type="primary", disabled=not can_next):
        st.switch_page("pages/3_run_models.py")

st.caption("Save Alternatives + Criteria, then save Matrix + Weights to enable Next.")
st.divider()

# ----------------------------
# Preference Set (select or create)
# ----------------------------
st.subheader("Preference Set")

with engine.begin() as conn:
    prefs = conn.execute(
        text(
            """
            SELECT preference_set_id::text AS preference_set_id, name, type, status, created_at
            FROM preference_sets
            WHERE scenario_id = :sid
            ORDER BY created_at DESC
            """
        ),
        {"sid": scenario_id},
    ).mappings().all()

prefs = [dict(p) for p in prefs]

pref_options = ["Create new…"] + [p["preference_set_id"] for p in prefs]
default_pref = st.session_state.get("preference_set_id")
if not default_pref:
    default_pref = "Create new…" if not prefs else prefs[0]["preference_set_id"]

selected_pref = st.selectbox(
    "Select preference set",
    options=pref_options,
    index=pref_options.index(default_pref) if default_pref in pref_options else 0,
    format_func=lambda x: "Create new…" if x == "Create new…" else next(
        pp["name"] for pp in prefs if pp["preference_set_id"] == x
    ),
)

if selected_pref == "Create new…":
    new_pref_name = st.text_input("New preference set name", value="Default Weights")
    new_pref_type = st.selectbox("Type", options=["direct"], index=0)

    if st.button("Create Preference Set", type="primary"):
        pref_id = pref_repo.get_or_create_preference_set(
            scenario_id=scenario_id,
            name=new_pref_name.strip() or "Default Weights",
            pref_type=new_pref_type,
            created_by=user_name,
        )
        st.session_state["preference_set_id"] = pref_id
        st.success(f"Preference set created: {pref_id}")
        st.rerun()
else:
    st.session_state["preference_set_id"] = selected_pref

pref_id = st.session_state.get("preference_set_id")
if not pref_id:
    st.info("Create or select a preference set to continue.")
    st.stop()

st.divider()

# ----------------------------
# Load existing state from DB
# ----------------------------
existing_alts = alt_repo.list_by_scenario(scenario_id)
existing_crit = crit_repo.list_by_scenario(scenario_id)

alt_names_existing = [a["name"] for a in existing_alts] if existing_alts else []
crit_rows_existing = existing_crit if existing_crit else []

# ----------------------------
# Alternatives
# ----------------------------
st.subheader("Alternatives")

default_alts = alt_names_existing or ["Alfred", "Beverly", "Calvin", "Diane", "Edward", "Fran"]
alts_df = pd.DataFrame({"Alternative Name": default_alts})

alts_df = st.data_editor(
    alts_df,
    num_rows="dynamic",
    use_container_width=True,
    key="alts_editor_step2",
)

alt_names = [str(x).strip() for x in alts_df["Alternative Name"].dropna().tolist() if str(x).strip()]
alt_names = list(dict.fromkeys(alt_names))

st.divider()

# ----------------------------
# Criteria (dropdown for Scale Type and Unit, single Description)
# ----------------------------
st.subheader("Criteria")

UNIT_OPTIONS = [
    "score", "points", "rank", "rating",
    "USD", "percent", "days", "hours", "minutes",
    "ms", "seconds", "kg", "g", "km", "m",
    "Yes/No", "count", "other",
]

SCALE_OPTIONS = ["ratio", "interval", "ordinal", "binary"]
DIRECTION_OPTIONS = ["benefit", "cost"]

if crit_rows_existing:
    crit_df = pd.DataFrame({
        "Criterion Name": [c["name"] for c in crit_rows_existing],
        "Direction": [c["direction"] for c in crit_rows_existing],
        "Scale Type": [c["scale_type"] for c in crit_rows_existing],
        "Unit": [c["unit"] if c["unit"] else "score" for c in crit_rows_existing],
        "Description": [c["description"] if c["description"] else "" for c in crit_rows_existing],
    })
else:
    crit_df = pd.DataFrame({
        "Criterion Name": ["GRE", "GPA", "College ranking", "Recommendation Rating", "Interview Rating"],
        "Direction": ["benefit"] * 5,
        "Scale Type": ["ratio", "ratio", "ordinal", "ordinal", "ordinal"],
        "Unit": ["score", "points", "rank", "rating", "rating"],
        "Description": ["", "", "", "", ""],
    })

crit_df = st.data_editor(
    crit_df,
    num_rows="dynamic",
    use_container_width=True,
    key="crit_editor_step2",
    column_config={
        "Direction": st.column_config.SelectboxColumn("Direction", options=DIRECTION_OPTIONS),
        "Scale Type": st.column_config.SelectboxColumn("Scale Type", options=SCALE_OPTIONS),
        "Unit": st.column_config.SelectboxColumn("Unit", options=UNIT_OPTIONS),
        "Description": st.column_config.TextColumn("Description"),
    },
)

crit_rows = []
for _, r in crit_df.iterrows():
    name = str(r.get("Criterion Name", "")).strip()
    if not name:
        continue

    unit_val = str(r.get("Unit", "")).strip()
    if unit_val == "other":
        unit_val = None

    crit_rows.append({
        "name": name,
        "direction": str(r.get("Direction", "benefit")).strip(),
        "scale_type": str(r.get("Scale Type", "ratio")).strip(),
        "unit": unit_val,
        "description": str(r.get("Description", "")).strip() or None,
    })

crit_names = [c["name"] for c in crit_rows]
crit_names = list(dict.fromkeys(crit_names))

st.divider()

# ----------------------------
# Save alternatives + criteria
# ----------------------------
save_left, save_right = st.columns([1, 2])

with save_left:
    if st.button("Save Alternatives + Criteria", type="primary"):
        if not alt_names:
            st.error("Please provide at least 1 alternative.")
            st.stop()
        if not crit_rows:
            st.error("Please provide at least 1 criterion.")
            st.stop()

        alt_repo.upsert_by_names(scenario_id, alt_names)
        crit_repo.upsert_rows(scenario_id, crit_rows)

        alt_repo.delete_missing(scenario_id, alt_names)
        crit_repo.delete_missing(scenario_id, crit_names)

        st.session_state["data_ready"] = False
        st.success("Saved. Now fill Matrix and Weights and save to enable Next.")
        st.rerun()

with save_right:
    st.caption("If you change alternatives or criteria later, save Matrix + Weights again before running models.")

# Reload after save
existing_alts = alt_repo.list_by_scenario(scenario_id)
existing_crit = crit_repo.list_by_scenario(scenario_id)
alt_names_db = [a["name"] for a in existing_alts]
crit_names_db = [c["name"] for c in existing_crit]

if not alt_names_db or not crit_names_db:
    st.info("Save alternatives and criteria first to unlock the matrix editor.")
    st.stop()

st.divider()

# ----------------------------
# Matrix editor
# ----------------------------
st.subheader("Performance Matrix (numeric)")

existing_matrix = meas_repo.load_matrix_ui(scenario_id)
if existing_matrix.empty:
    matrix_ui = pd.DataFrame(index=alt_names_db, columns=crit_names_db, dtype=float)
else:
    matrix_ui = existing_matrix.reindex(index=alt_names_db, columns=crit_names_db)

matrix_ui = st.data_editor(matrix_ui, use_container_width=True, key="matrix_editor_step2")

st.divider()

# ----------------------------
# Weights editor
# ----------------------------
st.subheader("Weights")

existing_weights = pref_repo.load_weights_by_criterion_name(pref_id)
weights_by_name = {}

wcols = st.columns(min(5, len(crit_names_db)))
for i, cname in enumerate(crit_names_db):
    with wcols[i % len(wcols)]:
        weights_by_name[cname] = st.number_input(
            f"{cname}",
            min_value=0.0,
            value=float(existing_weights.get(cname, 1.0)),
            step=0.05,
            key=f"w_step2_{pref_id}_{cname}",
        )

auto_normalize = st.checkbox("Auto-normalize weights to sum to 1", value=True)

st.divider()

# ----------------------------
# Save matrix + weights
# ----------------------------
if st.button("Save Matrix + Weights", type="primary"):
    if matrix_ui.isna().any().any():
        st.error("Matrix has missing cells. Fill all values before saving.")
        st.stop()

    try:
        matrix_numeric = matrix_ui.astype(float)
    except Exception:
        st.error("Matrix must be numeric in every cell.")
        st.stop()

    w_vals = np.array([float(weights_by_name[c]) for c in crit_names_db], dtype=float)
    if auto_normalize:
        s = float(w_vals.sum())
        if s <= 0:
            st.error("Weights must sum to a positive number.")
            st.stop()
        w_vals = w_vals / s

    weights_final = {crit_names_db[i]: float(w_vals[i]) for i in range(len(crit_names_db))}

    alt_map = alt_repo.upsert_by_names(scenario_id, alt_names_db)
    crit_map = crit_repo.upsert_rows(
        scenario_id,
        [
            {
                "name": c["name"],
                "direction": c["direction"],
                "scale_type": c["scale_type"],
                "unit": c["unit"],
                "description": c["description"],
            }
            for c in existing_crit
        ],
    )

    meas_repo.replace_all_for_scenario(scenario_id, alt_map, crit_map, matrix_numeric)
    pref_repo.replace_weights(pref_id, crit_map, weights_final)

    st.session_state["data_ready"] = True
    st.success("Saved matrix and weights. You can now proceed to Step 3.")
