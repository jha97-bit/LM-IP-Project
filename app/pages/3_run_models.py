import bootstrap

import hashlib
import numpy as np
import streamlit as st
from sqlalchemy import text

from core.topsis import compute_topsis
from persistence.engine import get_engine
from services.scenario_service import ScenarioService
from persistence.repositories.result_repo import ResultRepo
from persistence.repositories.topsis_repo import TopsisRepo

st.title("Step 3: Run Models")

ENGINE_VERSION = "core=0.1.0"

engine = get_engine()
scenario_id = st.session_state.get("scenario_id")
user_name = st.session_state.get("user_name", "")

if not scenario_id:
    st.info("Go to Step 1 and select a Scenario first.")
    st.stop()

# ----------------------------
# Navigation
# ----------------------------
nav_left, nav_right = st.columns(2)
with nav_left:
    if st.button("Back: Step 2 (Data Input)"):
        st.switch_page("pages/2_data_input.py")
with nav_right:
    if st.button("Next: Step 4 (Results)"):
        st.switch_page("pages/4_results.py")

st.divider()

# ----------------------------
# Preference set dropdown (searchable via multiselect max=1)
# ----------------------------
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

pref_ids = [p["preference_set_id"] for p in prefs]
pref_id_to_name = {p["preference_set_id"]: p["name"] for p in prefs}

default_pref = st.session_state.get("preference_set_id") or pref_ids[0]
picked_pref = st.multiselect(
    "Preference set",
    options=pref_ids,
    default=[default_pref] if default_pref in pref_ids else [pref_ids[0]],
    max_selections=1,
    format_func=lambda x: pref_id_to_name.get(x, x),
    key=f"pref_pick_step3_{scenario_id}",
)
pref_id = picked_pref[0] if picked_pref else pref_ids[0]
st.session_state["preference_set_id"] = pref_id

# Model dropdown (searchable)
model_options = ["TOPSIS"]
picked_model = st.multiselect(
    "Model to run",
    options=model_options,
    default=["TOPSIS"],
    max_selections=1,
    key=f"model_pick_step3_{scenario_id}",
)
model = picked_model[0] if picked_model else "TOPSIS"

scenario_service = ScenarioService(engine)
result_repo = ResultRepo(engine)
topsis_repo = TopsisRepo(engine)

# Reset preview if key inputs changed (scenario/pref/model)
preview_key = f"{scenario_id}|{pref_id}|{model}"
if st.session_state.get("preview_key") != preview_key:
    st.session_state["preview_key"] = preview_key
    st.session_state.pop("topsis_preview", None)
    st.session_state.pop("dup_check", None)

# ----------------------------
# Load + validate scenario data
# ----------------------------
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

# ----------------------------
# Signature helpers (Option B uses runs.input_signature)
# ----------------------------
def compute_input_signature() -> str:
    w = data.weights.astype(float)
    w = w / (float(w.sum()) + 1e-12)

    mat = np.round(data.matrix.astype(float), 12)
    w = np.round(w, 12)

    h = hashlib.sha256()
    h.update(("alts:" + "|".join(data.alternative_ids)).encode("utf-8"))
    h.update(("crits:" + "|".join(data.criterion_ids)).encode("utf-8"))
    h.update(("dirs:" + "|".join(data.directions)).encode("utf-8"))
    h.update(mat.tobytes(order="C"))
    h.update(w.tobytes(order="C"))
    return h.hexdigest()

def find_existing_identical_run(sig: str) -> tuple[str | None, dict | None]:
    with engine.begin() as conn:
        row = conn.execute(
            text("""
                SELECT run_id::text AS run_id, executed_at, executed_by, run_label, input_signature
                FROM runs
                WHERE scenario_id = :sid
                  AND preference_set_id = :pid
                  AND method = 'topsis'
                  AND input_signature = :sig
                ORDER BY executed_at DESC
                LIMIT 1
            """),
            {"sid": scenario_id, "pid": pref_id, "sig": sig},
        ).mappings().first()

    if not row:
        return None, None
    return str(row["run_id"]), dict(row)

# ----------------------------
# Run label input (stored in runs.run_label)
# ----------------------------
st.divider()
st.subheader("Run Label")

default_label = st.session_state.get("run_label_default")
if not default_label:
    default_label = f"{pref_id_to_name.get(pref_id, 'Preference')}-v1"
st.session_state["run_label_default"] = default_label

run_label = st.text_input(
    "Name this run (optional)",
    value=default_label,
    help="Example: BaseCase-v1, WeightsTweaked, ScenarioB-test2",
)

# ----------------------------
# Preview Run (no DB write)
# ----------------------------
st.divider()
st.subheader("Run Preview")

colA, colB = st.columns([1, 1])
with colA:
    run_preview = st.button("Run (Preview)", type="primary")
with colB:
    clear_preview = st.button("Clear Preview")

if clear_preview:
    st.session_state.pop("topsis_preview", None)
    st.session_state.pop("dup_check", None)
    st.info("Preview cleared.")
    st.rerun()

if run_preview:
    if model != "TOPSIS":
        st.error("Only TOPSIS is enabled right now.")
        st.stop()

    current_sig = compute_input_signature()

    w = data.weights.astype(float)
    w = w / (float(w.sum()) + 1e-12)

    artifacts = compute_topsis(
        matrix=data.matrix.astype(float),
        weights=w,
        directions=data.directions,
    )

    # Ranking preview
    alt_scores = []
    for i, alt_name in enumerate(data.alternative_names):
        alt_scores.append({"alternative_name": alt_name, "score": float(artifacts.c_star[i])})

    alt_scores = sorted(alt_scores, key=lambda r: r["score"], reverse=True)
    for i, r in enumerate(alt_scores, start=1):
        r["rank"] = i

    # Duplicate check only after preview
    existing_run_id, existing_meta = find_existing_identical_run(current_sig)

    st.session_state["dup_check"] = {
        "sig": current_sig,
        "existing_run_id": existing_run_id,
        "existing_meta": existing_meta,
    }

    st.session_state["topsis_preview"] = {
        "sig": current_sig,
        "scores": alt_scores,
        "artifacts": artifacts,
    }

    st.success("Preview computed. Review ranking, then Save.")
    st.rerun()

preview = st.session_state.get("topsis_preview")
dup_check = st.session_state.get("dup_check")

if preview:
    st.subheader("Preview Ranking")
    st.dataframe(preview["scores"], width="stretch")

# ----------------------------
# Save (DB write) with overwrite choice
# ----------------------------
st.divider()
st.subheader("Save")

save_disabled = preview is None
overwrite = False

if preview and dup_check and dup_check.get("existing_run_id"):
    meta = dup_check.get("existing_meta") or {}
    st.warning("Identical run already exists for this preference set (same matrix + weights).")
    st.write(
        {
            "existing_run_id": dup_check["existing_run_id"],
            "existing_label": meta.get("run_label"),
            "executed_at": str(meta.get("executed_at")),
            "executed_by": meta.get("executed_by"),
        }
    )
    overwrite = st.checkbox("Overwrite existing run instead of creating a new one", value=True)

save_btn = st.button("Save Results", disabled=save_disabled)

def persist_artifacts_to_run(run_id: str, artifacts) -> None:
    topsis_repo.save_run_config(run_id, normalization="vector", distance="euclidean")

    alt_id_to_score = {data.alternative_ids[i]: float(artifacts.c_star[i]) for i in range(len(data.alternative_ids))}
    result_repo.replace_scores(run_id, alt_id_to_score)

    norm_rows = []
    w_rows = []
    ideal_rows = []
    dist_rows = []

    m, n = data.matrix.shape
    for i in range(m):
        for j in range(n):
            norm_rows.append({
                "run_id": run_id,
                "alternative_id": data.alternative_ids[i],
                "criterion_id": data.criterion_ids[j],
                "value": float(artifacts.normalized_matrix[i, j]),
            })
            w_rows.append({
                "run_id": run_id,
                "alternative_id": data.alternative_ids[i],
                "criterion_id": data.criterion_ids[j],
                "value": float(artifacts.weighted_matrix[i, j]),
            })

    for j in range(n):
        ideal_rows.append({
            "run_id": run_id,
            "criterion_id": data.criterion_ids[j],
            "pos_ideal": float(artifacts.pis[j]),
            "neg_ideal": float(artifacts.nis[j]),
        })

    for i in range(m):
        dist_rows.append({
            "run_id": run_id,
            "alternative_id": data.alternative_ids[i],
            "s_pos": float(artifacts.s_pos[i]),
            "s_neg": float(artifacts.s_neg[i]),
            "c_star": float(artifacts.c_star[i]),
        })

    topsis_repo.replace_normalized(run_id, norm_rows)
    topsis_repo.replace_weighted(run_id, w_rows)
    topsis_repo.replace_ideals(run_id, ideal_rows)
    topsis_repo.replace_distances(run_id, dist_rows)

if save_btn:
    if preview is None:
        st.error("Run a preview first, then save.")
        st.stop()

    # Force preview again if inputs changed
    current_sig_now = compute_input_signature()
    if preview.get("sig") != current_sig_now:
        st.error("Inputs changed since preview. Please run preview again before saving.")
        st.stop()

    artifacts = preview["artifacts"]
    sig = preview["sig"]

    # Normalize label
    label_clean = (run_label or "").strip() or None

    existing_run_id = dup_check.get("existing_run_id") if dup_check else None

    if existing_run_id and overwrite:
        with engine.begin() as conn:
            conn.execute(
                text("""
                    UPDATE runs
                    SET executed_at = now(),
                        executed_by = :by,
                        engine_version = :ev,
                        input_signature = :sig,
                        run_label = :lbl
                    WHERE run_id = :rid
                """),
                {
                    "by": user_name,
                    "ev": ENGINE_VERSION,
                    "sig": sig,
                    "lbl": label_clean,
                    "rid": existing_run_id,
                },
            )

        persist_artifacts_to_run(existing_run_id, artifacts)
        run_id = existing_run_id
        st.success(f"Saved by overwriting existing run: {run_id}")
    else:
        with engine.begin() as conn:
            row = conn.execute(
                text("""
                    INSERT INTO runs (scenario_id, preference_set_id, method, engine_version, executed_by, input_signature, run_label)
                    VALUES (:sid, :pid, 'topsis', :ev, :by, :sig, :lbl)
                    RETURNING run_id::text AS run_id
                """),
                {
                    "sid": scenario_id,
                    "pid": pref_id,
                    "ev": ENGINE_VERSION,
                    "by": user_name,
                    "sig": sig,
                    "lbl": label_clean,
                },
            ).mappings().first()

        run_id = str(row["run_id"])
        persist_artifacts_to_run(run_id, artifacts)
        st.success(f"Saved as a new run: {run_id}")

    st.session_state["last_run_id"] = run_id

    # Clear preview state
    st.session_state.pop("topsis_preview", None)
    st.session_state.pop("dup_check", None)

    if st.button("View Results"):
        st.switch_page("pages/4_results.py")
