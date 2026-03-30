"""
Shared UI for unified Step 3 (Run Model). Used by pages/3_run_models.py.
"""
from __future__ import annotations

import hashlib

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st
from sqlalchemy import text

from app.ui_theme import BLUE_SCALE, BLUE_TEAL_SCALE, DISCRETE_PALETTE
from core.topsis import compute_topsis
from core.vft_model import Attribute
from persistence.repositories.alternative_repo import AlternativeRepo
from persistence.repositories.criterion_repo import CriterionRepo
from persistence.repositories.measurement_repo import MeasurementRepo
from persistence.repositories.preference_repo import PreferenceRepo
from persistence.repositories.result_repo import ResultRepo
from persistence.repositories.topsis_repo import TopsisRepo
from services.scenario_service import ScenarioService
from services.vft_service import VFTService


ENGINE_VERSION_TOPSIS = "core=0.1.0"


def render_topsis_run(engine, scenario_id: str, user_name: str) -> None:
    st.subheader("📐 TOPSIS")
    st.caption("Preview the TOPSIS run against your data, then save to persist results.")
    nav_left, nav_right = st.columns(2)
    with nav_left:
        if st.button("← Step 2: Data Input", key="topsis_nav_back"):
            st.switch_page("pages/2_data_input.py")
    with nav_right:
        if st.button("Next: Results →", type="primary", key="topsis_nav_next"):
            st.switch_page("pages/4_results.py")
    st.divider()

    with engine.begin() as conn:
        prefs = conn.execute(
            text("""
                SELECT preference_set_id::text AS preference_set_id, name, type, status, created_at
                FROM preference_sets WHERE scenario_id = :sid ORDER BY created_at DESC
            """),
            {"sid": scenario_id},
        ).mappings().all()
    prefs = [dict(p) for p in prefs]

    if not prefs:
        st.warning("No preference sets found. Go to Step 2 and create one with weights.")
        st.stop()

    pref_ids = [p["preference_set_id"] for p in prefs]
    pref_id_to_name = {p["preference_set_id"]: p["name"] for p in prefs}

    default_pref = st.session_state.get("preference_set_id") or pref_ids[0]
    if default_pref not in pref_ids:
        default_pref = pref_ids[0]

    col_pref, col_label = st.columns(2)
    with col_pref:
        picked_pref = st.multiselect(
            "Preference set",
            options=pref_ids,
            default=[default_pref],
            max_selections=1,
            format_func=lambda x: pref_id_to_name.get(x, x),
            key=f"pref_pick_step3_{scenario_id}",
        )
        pref_id = picked_pref[0] if picked_pref else pref_ids[0]
        st.session_state["preference_set_id"] = pref_id

    with col_label:
        default_label = f"{pref_id_to_name.get(pref_id, 'Run')}-v1"
        run_label = st.text_input(
            "Run label (optional)",
            value=st.session_state.get("run_label_default", default_label),
            placeholder="e.g. BaseCase-v1, CostFocus-v2",
        )
        st.session_state["run_label_default"] = run_label

    scenario_service = ScenarioService(engine)
    result_repo = ResultRepo(engine)
    topsis_repo = TopsisRepo(engine)

    preview_key = f"{scenario_id}|{pref_id}|topsis"
    if st.session_state.get("preview_key") != preview_key:
        st.session_state["preview_key"] = preview_key
        st.session_state.pop("topsis_preview", None)
        st.session_state.pop("dup_check", None)

    try:
        data = scenario_service.load(scenario_id, pref_id)
        ok, issues = scenario_service.validate(data)
    except Exception as e:
        st.warning(str(e))
        st.stop()

    st.subheader("Validation")
    if ok:
        st.success("✅ Scenario data is complete and ready to run.")
    else:
        for msg in issues:
            st.warning(msg)
        st.stop()

    with st.expander("View input summary", expanded=False):
        meas_repo = MeasurementRepo(engine)
        pref_repo = PreferenceRepo(engine)
        mat = meas_repo.load_matrix_ui(scenario_id)
        wts = pref_repo.load_weights_by_criterion_name(pref_id)
        if not mat.empty:
            wt_row = pd.DataFrame([{c: wts.get(c, 0.0) for c in mat.columns}], index=["Weight"])
            st.dataframe(pd.concat([wt_row, mat]), use_container_width=True)

    def compute_input_signature() -> str:
        w = data.weights.astype(float)
        w = w / (float(w.sum()) + 1e-12)
        mat = np.round(data.matrix.astype(float), 12)
        w = np.round(w, 12)
        h = hashlib.sha256()
        h.update(("alts:" + "|".join(data.alternative_ids)).encode())
        h.update(("crits:" + "|".join(data.criterion_ids)).encode())
        h.update(("dirs:" + "|".join(data.directions)).encode())
        h.update(mat.tobytes(order="C"))
        h.update(w.tobytes(order="C"))
        return h.hexdigest()

    def find_existing_identical_run(sig: str):
        with engine.begin() as conn:
            row = conn.execute(
                text("""
                    SELECT run_id::text AS run_id, executed_at, executed_by, run_label
                    FROM runs
                    WHERE scenario_id = :sid AND preference_set_id = :pid
                      AND method = 'topsis' AND input_signature = :sig
                    ORDER BY executed_at DESC LIMIT 1
                """),
                {"sid": scenario_id, "pid": pref_id, "sig": sig},
            ).mappings().first()
        if not row:
            return None, None
        return str(row["run_id"]), dict(row)

    st.divider()
    st.subheader("Run Preview")

    colA, colB = st.columns(2)
    with colA:
        run_preview = st.button("▶ Preview Run", type="primary", key="topsis_preview_btn")
    with colB:
        if st.button("✕ Clear Preview", key="topsis_clear_preview"):
            st.session_state.pop("topsis_preview", None)
            st.session_state.pop("dup_check", None)
            st.rerun()

    if run_preview:
        sig = compute_input_signature()
        w = data.weights.astype(float)
        w = w / (float(w.sum()) + 1e-12)
        artifacts = compute_topsis(
            matrix=data.matrix.astype(float),
            weights=w,
            directions=data.directions,
        )
        alt_scores = sorted(
            [
                {"alternative_name": data.alternative_names[i], "score": float(artifacts.c_star[i])}
                for i in range(len(data.alternative_names))
            ],
            key=lambda r: r["score"],
            reverse=True,
        )
        for i, r in enumerate(alt_scores, 1):
            r["rank"] = i

        existing_run_id, existing_meta = find_existing_identical_run(sig)
        st.session_state["dup_check"] = {"sig": sig, "existing_run_id": existing_run_id, "existing_meta": existing_meta}
        st.session_state["topsis_preview"] = {"sig": sig, "scores": alt_scores, "artifacts": artifacts}
        st.rerun()

    preview = st.session_state.get("topsis_preview")
    dup_check = st.session_state.get("dup_check")

    if preview:
        st.subheader("Preview Ranking")
        scores_df = pd.DataFrame(preview["scores"])
        fig = px.bar(
            scores_df.sort_values("rank"),
            x="alternative_name",
            y="score",
            color="score",
            color_continuous_scale=BLUE_SCALE,
            title="TOPSIS Score C* Preview",
            labels={"alternative_name": "Alternative", "score": "C* Score"},
        )
        fig.update_layout(showlegend=False, height=340, margin=dict(l=10, r=10, t=40, b=10))
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(scores_df, use_container_width=True)

    st.divider()
    st.subheader("Save Results")

    save_disabled = preview is None
    overwrite = False

    if preview and dup_check and dup_check.get("existing_run_id"):
        meta = dup_check.get("existing_meta") or {}
        st.warning("⚠ Identical run already exists (same matrix + weights fingerprint).")
        st.caption(
            f"Existing run: {dup_check['existing_run_id'][:8]}… by {meta.get('executed_by', '?')} "
            f"at {str(meta.get('executed_at', '?'))[:16]}"
        )
        overwrite = st.checkbox("Overwrite existing run instead of creating a new one", value=True)

    if st.button("💾 Save Results to Database", type="primary", disabled=save_disabled, key="topsis_save"):
        if preview is None:
            st.warning("Run a preview first.")
            st.stop()

        current_sig = compute_input_signature()
        if preview.get("sig") != current_sig:
            st.warning("Inputs changed since preview — run preview again.")
            st.stop()

        artifacts = preview["artifacts"]
        sig = preview["sig"]
        label_clean = (run_label or "").strip() or None
        existing_run_id = dup_check.get("existing_run_id") if dup_check else None

        def persist(run_id):
            topsis_repo.save_run_config(run_id, normalization="vector", distance="euclidean")
            alt_id_to_score = {data.alternative_ids[i]: float(artifacts.c_star[i]) for i in range(len(data.alternative_ids))}
            result_repo.replace_scores(run_id, alt_id_to_score)
            m, n = data.matrix.shape
            norm_rows, w_rows, ideal_rows, dist_rows = [], [], [], []
            for i in range(m):
                for j in range(n):
                    norm_rows.append(
                        {
                            "run_id": run_id,
                            "alternative_id": data.alternative_ids[i],
                            "criterion_id": data.criterion_ids[j],
                            "value": float(artifacts.normalized_matrix[i, j]),
                        }
                    )
                    w_rows.append(
                        {
                            "run_id": run_id,
                            "alternative_id": data.alternative_ids[i],
                            "criterion_id": data.criterion_ids[j],
                            "value": float(artifacts.weighted_matrix[i, j]),
                        }
                    )
            for j in range(n):
                ideal_rows.append(
                    {
                        "run_id": run_id,
                        "criterion_id": data.criterion_ids[j],
                        "pos_ideal": float(artifacts.pis[j]),
                        "neg_ideal": float(artifacts.nis[j]),
                    }
                )
            for i in range(m):
                dist_rows.append(
                    {
                        "run_id": run_id,
                        "alternative_id": data.alternative_ids[i],
                        "s_pos": float(artifacts.s_pos[i]),
                        "s_neg": float(artifacts.s_neg[i]),
                        "c_star": float(artifacts.c_star[i]),
                    }
                )
            topsis_repo.replace_normalized(run_id, norm_rows)
            topsis_repo.replace_weighted(run_id, w_rows)
            topsis_repo.replace_ideals(run_id, ideal_rows)
            topsis_repo.replace_distances(run_id, dist_rows)

        if existing_run_id and overwrite:
            with engine.begin() as conn:
                conn.execute(
                    text("""
                        UPDATE runs SET executed_at=now(), executed_by=:by,
                            engine_version=:ev, input_signature=:sig, run_label=:lbl
                        WHERE run_id=:rid
                    """),
                    {
                        "by": user_name,
                        "ev": ENGINE_VERSION_TOPSIS,
                        "sig": sig,
                        "lbl": label_clean,
                        "rid": existing_run_id,
                    },
                )
            persist(existing_run_id)
            run_id = existing_run_id
            st.success(f"✅ Updated existing run: {run_id[:8]}…")
        else:
            with engine.begin() as conn:
                row = conn.execute(
                    text("""
                        INSERT INTO runs (scenario_id, preference_set_id, method, engine_version,
                                         executed_by, input_signature, run_label)
                        VALUES (:sid, :pid, 'topsis', :ev, :by, :sig, :lbl)
                        RETURNING run_id::text AS run_id
                    """),
                    {
                        "sid": scenario_id,
                        "pid": pref_id,
                        "ev": ENGINE_VERSION_TOPSIS,
                        "by": user_name,
                        "sig": sig,
                        "lbl": label_clean,
                    },
                ).mappings().first()
            run_id = str(row["run_id"])
            persist(run_id)
            st.success(f"✅ Saved new run: {run_id[:8]}…")

        st.session_state["last_run_id"] = run_id
        st.session_state.pop("topsis_preview", None)
        st.session_state.pop("dup_check", None)
        st.toast("✅ TOPSIS run saved! Redirecting to Results…", icon="🏆")
        st.switch_page("pages/4_results.py")


def render_vft_run(engine, scenario_id: str, user_name: str) -> None:
    st.subheader("📈 VFT — Value Function Transformation")
    st.caption("Preview the VFT scoring, then save to persist results.")

    alt_repo = AlternativeRepo(engine)
    crit_repo = CriterionRepo(engine)
    meas_repo = MeasurementRepo(engine)
    pref_repo = PreferenceRepo(engine)
    vft_svc = VFTService(engine)

    nav_left, nav_right = st.columns(2)
    with nav_left:
        if st.button("← Step 3: Value Functions", key="vft_nav_back"):
            st.switch_page("pages/3b_vft_value_functions.py")
    with nav_right:
        if st.button("Next: Results →", type="primary", key="vft_nav_next"):
            st.switch_page("pages/4_results.py")
    st.divider()

    existing_crit = crit_repo.list_by_scenario(scenario_id)
    existing_alts = alt_repo.list_by_scenario(scenario_id)
    matrix_df = meas_repo.load_matrix_ui(scenario_id)

    if not existing_crit or not existing_alts:
        st.warning("No alternatives or criteria found. Complete Step 2 first.")
        st.stop()
    if matrix_df.empty or matrix_df.isna().any().any():
        st.warning("Performance matrix is incomplete. Fill all values in Step 2.")
        st.stop()

    existing_vfs = vft_svc.load_value_functions(scenario_id)
    crit_names = [c["name"] for c in existing_crit]

    attributes = []
    for crit in existing_crit:
        cname = crit["name"]
        vf = existing_vfs.get(cname, {})
        if not matrix_df.empty and cname in matrix_df.columns:
            data_min = float(matrix_df[cname].dropna().min())
            data_max = float(matrix_df[cname].dropna().max())
        else:
            data_min, data_max = 0.0, 100.0

        if vf:
            pts = sorted(vf.get("points", []), key=lambda p: p[0])
            ft = vf.get("function_type", "linear")
            if ft == "piecewise_linear":
                attr = Attribute(
                    name=cname,
                    min_val=data_min,
                    max_val=data_max,
                    scaling_type="Custom",
                    custom_points=pts,
                )
            else:
                if len(pts) >= 2:
                    min_val = float(pts[0][0])
                    max_val = float(pts[-1][0])
                    is_inc = float(pts[-1][1]) >= float(pts[0][1])
                else:
                    min_val = data_min
                    max_val = data_max
                    is_inc = crit.get("direction") == "benefit"

                if max_val <= min_val:
                    max_val = min_val + 1.0

                attr = Attribute(
                    name=cname,
                    min_val=min_val,
                    max_val=max_val,
                    scaling_type="Linear",
                    scaling_direction="Increasing" if is_inc else "Decreasing",
                )
        else:
            is_inc = crit.get("direction") == "benefit"
            attr = Attribute(
                name=cname,
                min_val=data_min,
                max_val=data_max,
                scaling_type="Linear",
                scaling_direction="Increasing" if is_inc else "Decreasing",
            )
        attributes.append(attr)

    with engine.begin() as conn:
        prefs = conn.execute(
            text("""
                SELECT preference_set_id::text AS preference_set_id, name
                FROM preference_sets WHERE scenario_id = :sid ORDER BY created_at DESC
            """),
            {"sid": scenario_id},
        ).mappings().all()
    prefs = [dict(p) for p in prefs]

    if not prefs:
        st.warning("No preference sets found. Go to Step 2 to create one.")
        st.stop()

    pref_ids = [p["preference_set_id"] for p in prefs]
    pref_id_to_name = {p["preference_set_id"]: p["name"] for p in prefs}

    default_pref = st.session_state.get("preference_set_id") or pref_ids[0]
    if default_pref not in pref_ids:
        default_pref = pref_ids[0]

    col_pref, col_label = st.columns(2)
    with col_pref:
        picked_pref = st.multiselect(
            "Preference set",
            options=pref_ids,
            default=[default_pref],
            max_selections=1,
            format_func=lambda x: pref_id_to_name.get(x, x),
            key=f"pref_pick_vft_{scenario_id}",
        )
        pref_id = picked_pref[0] if picked_pref else pref_ids[0]
        st.session_state["preference_set_id"] = pref_id

    with col_label:
        run_label = st.text_input(
            "Run label (optional)",
            value=st.session_state.get("run_label_default_vft", f"{pref_id_to_name.get(pref_id, 'VFT')}-v1"),
        )
        st.session_state["run_label_default_vft"] = run_label

    weights = pref_repo.load_weights_by_criterion_name(pref_id)
    if not weights:
        st.warning("No weights found for this preference set. Go to Step 2 and save weights.")
        st.stop()

    w_total = sum(float(weights.get(c.name, 0.0)) for c in attributes)
    for attr in attributes:
        w_raw = float(weights.get(attr.name, 0.0))
        attr.weight = w_raw / w_total if w_total > 0 else 1.0 / len(attributes)
        attr.swing_weight = attr.weight * 100

    def compute_preview():
        utility_matrix = {}
        weighted_matrix = {}
        total_scores = {}
        attr_by_name = {a.name: a for a in attributes}

        for alt_name in matrix_df.index:
            utility_matrix[alt_name] = {}
            weighted_matrix[alt_name] = {}
            total = 0.0
            for crit_name in matrix_df.columns:
                raw = float(matrix_df.loc[alt_name, crit_name])
                attr = attr_by_name.get(crit_name)
                u = attr.get_value(raw) if attr else 0.0
                w = float(weights.get(crit_name, 0.0))
                if w_total > 0:
                    w = w / w_total
                utility_matrix[alt_name][crit_name] = u
                weighted_matrix[alt_name][crit_name] = u * w
                total += u * w
            total_scores[alt_name] = total

        return utility_matrix, weighted_matrix, total_scores

    st.divider()
    st.subheader("Run Preview")

    if st.button("▶ Preview VFT Scoring", type="primary", key="vft_preview_btn"):
        utility_matrix, weighted_matrix, total_scores = compute_preview()
        st.session_state["vft_preview"] = {
            "utility_matrix": utility_matrix,
            "weighted_matrix": weighted_matrix,
            "total_scores": total_scores,
        }
        st.rerun()

    if st.button("✕ Clear Preview", key="vft_clear_preview"):
        st.session_state.pop("vft_preview", None)
        st.rerun()

    preview = st.session_state.get("vft_preview")

    if preview:
        total_scores = preview["total_scores"]
        utility_matrix = preview["utility_matrix"]
        weighted_matrix = preview["weighted_matrix"]

        sorted_alts = sorted(total_scores.items(), key=lambda x: x[1], reverse=True)

        st.subheader("Preview Ranking")
        rank_df = pd.DataFrame(
            [{"Rank": i + 1, "Alternative": alt, "VFT Score": f"{sc:.4f}"} for i, (alt, sc) in enumerate(sorted_alts)]
        )

        bar_fig = px.bar(
            pd.DataFrame({"Alternative": [x[0] for x in sorted_alts], "Score": [x[1] for x in sorted_alts]}),
            x="Alternative",
            y="Score",
            color="Score",
            color_continuous_scale="Greens",
            title="VFT Total Score Preview",
        )
        bar_fig.update_layout(height=380)
        st.plotly_chart(bar_fig, use_container_width=True)

        st.dataframe(rank_df, use_container_width=True, hide_index=True)

        st.subheader("Utility Matrix (0-1)")
        util_df = pd.DataFrame(utility_matrix).T
        util_df = util_df[crit_names]
        st.dataframe(util_df.style.format("{:.4f}"), use_container_width=True)

        st.subheader("Weighted Contribution Matrix")
        weighted_df = pd.DataFrame(weighted_matrix).T
        weighted_df = weighted_df[crit_names]
        weighted_df["Total"] = weighted_df.sum(axis=1)
        st.dataframe(weighted_df.style.format("{:.4f}"), use_container_width=True)

        st.subheader("Contribution by Criterion")
        contrib_long = (
            weighted_df.drop(columns=["Total"])
            .reset_index()
            .melt(id_vars="index", var_name="Criterion", value_name="Contribution")
            .rename(columns={"index": "Alternative"})
        )

        stack_fig = px.bar(
            contrib_long,
            x="Alternative",
            y="Contribution",
            color="Criterion",
            title="Weighted Score Composition by Alternative",
            color_discrete_sequence=DISCRETE_PALETTE,
        )
        stack_fig.update_layout(barmode="stack", height=420)
        st.plotly_chart(stack_fig, use_container_width=True)

        st.divider()
        st.subheader("Save Run")

        if st.button("💾 Save VFT Run", type="primary", key="vft_save"):
            alt_map = {a["name"]: a["alternative_id"] for a in existing_alts}
            crit_map = {c["name"]: c["criterion_id"] for c in existing_crit}
            normalized_weights = {
                crit_name: (float(weights.get(crit_name, 0.0)) / w_total if w_total > 0 else 0.0)
                for crit_name in crit_names
            }

            run_id = vft_svc.run_and_persist(
                scenario_id=scenario_id,
                preference_set_id=pref_id,
                executed_by=user_name or None,
                matrix_df=matrix_df,
                weights=normalized_weights,
                attributes=attributes,
                alt_map=alt_map,
                crit_map=crit_map,
                run_label=run_label or None,
            )

            st.success(f"✅ VFT run saved successfully. Run ID: {str(run_id)[:8]}…")
            st.session_state["last_run_id"] = str(run_id)
            st.session_state["latest_run_method"] = "vft"
            st.session_state["latest_run_label"] = run_label
            st.session_state.pop("vft_preview", None)
            st.switch_page("pages/4_results.py")

    else:
        st.info("Click **Preview VFT Scoring** to compute the VFT utilities and total scores.")

    st.divider()
    col_prev, col_next = st.columns(2)
    with col_prev:
        if st.button("← Back to Value Functions", key="vft_run_back_bottom"):
            st.switch_page("pages/3b_vft_value_functions.py")
    with col_next:
        if st.button("Go to Results →", key="vft_run_results_bottom"):
            st.switch_page("pages/4_results.py")


def render_ahp_placeholder() -> None:
    st.subheader("⚖️ AHP — Analytic Hierarchy Process")
    st.info(
        "Pairwise comparison matrices, consistency checks, and eigenvector-derived weights are **not "
        "implemented in this build**. The schema reserves `ahp` as a method type for future integration "
        "with the shared `runs` / `result_scores` tables.\n\n"
        "**What you can do now:** create a **TOPSIS** or **VFT** scenario for runnable analysis, or enter "
        "judgment-based weights manually in Step 2 and run **VFT**."
    )
    nav_left, nav_right = st.columns(2)
    with nav_left:
        if st.button("← Step 2: Data Input", key="ahp_nav_back"):
            st.switch_page("pages/2_data_input.py")
    with nav_right:
        if st.button("Next: Results →", type="primary", key="ahp_nav_next"):
            st.switch_page("pages/4_results.py")
