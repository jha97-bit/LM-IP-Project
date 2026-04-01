import bootstrap  # noqa: F401

import numpy as np
import pandas as pd
import streamlit as st
from app.ui_theme import apply_theme, BLUE_SCALE, TEAL_SCALE, BLUE_TEAL_SCALE, DISCRETE_PALETTE, section_header
from app.app_context import guard_page, sync_method_from_scenario
from app.sidebar_nav import render_sidebar
import plotly.graph_objects as go
from sqlalchemy import text

from persistence.engine import get_engine
from persistence.repositories.alternative_repo import AlternativeRepo
from persistence.repositories.criterion_repo import CriterionRepo
from persistence.repositories.measurement_repo import MeasurementRepo
from persistence.repositories.preference_repo import PreferenceRepo

st.set_page_config(page_title="MCDA — Data Input", layout="wide")
st.title("Step 2: Data Input")
apply_theme()
section_header("Data Input", variant="gradient")

guard_page("pages/2_data_input.py", require_scenario=True)
sync_method_from_scenario()
render_sidebar("pages/2_data_input.py")

engine = get_engine()
alt_repo = AlternativeRepo(engine)
crit_repo = CriterionRepo(engine)
meas_repo = MeasurementRepo(engine)
pref_repo = PreferenceRepo(engine)

scenario_id = st.session_state.get("scenario_id")
user_name = st.session_state.get("user_name", "")
method_choice = st.session_state.get("method_choice", "topsis")

if not scenario_id:
    st.warning("No scenario selected — go to Step 1 first.")
    if st.button("← Go to Step 1", key="data_goto_step1"):
        st.switch_page("pages/1_decision_setup.py")
    st.stop()

st.session_state.setdefault("preference_set_id", None)
st.session_state.setdefault("data_ready", False)

# Navigation
nav_left, nav_right = st.columns(2)
with nav_left:
    if st.button("← Step 1: Decision & Scenario", key="nav_back_data"):
        st.switch_page("pages/1_decision_setup.py")
with nav_right:
    can_next = bool(st.session_state.get("data_ready"))
    if method_choice == "vft":
        next_page = "pages/3b_vft_value_functions.py"
        next_label = "Next: Value Functions →"
    else:
        next_page = "pages/3_run_models.py"
        next_label = "Next: Run Model →"
    if st.button(next_label, type="primary", disabled=not can_next, key="nav_next_data"):
        st.switch_page(next_page)

_badges = {"topsis": "TOPSIS", "vft": "VFT"}
method_badge = _badges.get(method_choice, method_choice.upper())
st.caption(f"Method: **{method_badge}** · Fill alternatives, criteria, matrix and preference weights, then Save.")
st.caption("Step 2 of 7 — build alternatives/criteria, then matrix, then preference weights.")
st.progress(2 / 7)
st.divider()

# ─── Load existing state ───────────────────────────────────────────────────────
existing_alts = alt_repo.list_by_scenario(scenario_id)
existing_crit = crit_repo.list_by_scenario(scenario_id)
alt_names_existing = [a["name"] for a in existing_alts] if existing_alts else []

tab_alts, tab_matrix, tab_prefs = st.tabs(["ALTERNATIVES & CRITERIA", "PERFORMANCE MATRIX", "PREFERENCE SETS & WEIGHTS"])

# ══════════════════════════════════════════════════════════════════════
# TAB 1: Alternatives & Criteria
# ══════════════════════════════════════════════════════════════════════
with tab_alts:
    st.markdown(
        "<div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:8px'>"
        "<span style='font-weight:600;color:#1E3A5F'>Input Structure</span>"
        "<span style='font-size:0.9rem;color:#475569'>Save → open <b>Performance Matrix</b> tab</span>"
        "</div>",
        unsafe_allow_html=True,
    )
    col_a, col_b = st.columns(2, gap="large")

    with col_a:
        st.markdown("<div class='input-card'>", unsafe_allow_html=True)
        section_header("Alternatives", variant="sub")
        st.caption("Each row is one option to evaluate.")
        default_alts = alt_names_existing or ["Option A", "Option B", "Option C"]
        alts_df = pd.DataFrame({"Alternative Name": default_alts})
        alts_df = st.data_editor(alts_df, num_rows="dynamic", use_container_width=True, key="alts_editor_step2")
        alt_names = [str(x).strip() for x in alts_df["Alternative Name"].dropna().tolist() if str(x).strip()]
        alt_names = list(dict.fromkeys(alt_names))
        st.markdown("</div>", unsafe_allow_html=True)

    with col_b:
        st.markdown("<div class='input-card'>", unsafe_allow_html=True)
        section_header("Criteria", variant="sub")
        UNIT_OPTIONS = ["score","points","rank","rating","USD","percent","days","hours",
                        "minutes","ms","seconds","kg","g","km","m","Yes/No","count","other"]
        SCALE_OPTIONS = ["ratio","interval","ordinal","binary"]

        # VFT uses Maximize/Minimize; TOPSIS uses benefit/cost
        if method_choice == "vft":
            st.caption("For VFT: specify whether higher values are better (Maximize) or worse (Minimize).")
            DIRECTION_OPTIONS_VFT = ["Maximize", "Minimize"]

            if existing_crit:
                def _dir_to_vft(d):
                    return "Maximize" if d == "benefit" else "Minimize"
                crit_df = pd.DataFrame({
                    "Criterion Name": [c["name"] for c in existing_crit],
                    "Direction": [_dir_to_vft(c["direction"]) for c in existing_crit],
                    "Scale Type": [c["scale_type"] for c in existing_crit],
                    "Unit": [c["unit"] if c["unit"] else "score" for c in existing_crit],
                    "Description": [c["description"] if c["description"] else "" for c in existing_crit],
                })
            else:
                crit_df = pd.DataFrame({
                    "Criterion Name": ["Criterion 1", "Criterion 2", "Criterion 3"],
                    "Direction": ["Maximize", "Maximize", "Minimize"],
                    "Scale Type": ["ratio", "ratio", "ratio"],
                    "Unit": ["score", "score", "USD"],
                    "Description": ["", "", ""],
                })
            crit_df = st.data_editor(
                crit_df, num_rows="dynamic", use_container_width=True, key="crit_editor_step2",
                column_config={
                    "Direction": st.column_config.SelectboxColumn("Direction (VFT)", options=DIRECTION_OPTIONS_VFT),
                    "Scale Type": st.column_config.SelectboxColumn("Scale Type", options=SCALE_OPTIONS),
                    "Unit": st.column_config.SelectboxColumn("Unit", options=UNIT_OPTIONS),
                    "Description": st.column_config.TextColumn("Description"),
                },
            )
            # Map VFT directions back to benefit/cost for storage
            def _vft_to_dir(d):
                return "benefit" if d in ("Maximize", "benefit") else "cost"
        else:
            st.caption("For TOPSIS: benefit = higher is better; cost = lower is better.")
            st.caption("ℹ️ Benefit means maximize. Cost means minimize.")
            DIRECTION_OPTIONS = ["benefit", "cost"]

            if existing_crit:
                crit_df = pd.DataFrame({
                    "Criterion Name": [c["name"] for c in existing_crit],
                    "Direction": [c["direction"] for c in existing_crit],
                    "Scale Type": [c["scale_type"] for c in existing_crit],
                    "Unit": [c["unit"] if c["unit"] else "score" for c in existing_crit],
                    "Description": [c["description"] if c["description"] else "" for c in existing_crit],
                })
            else:
                crit_df = pd.DataFrame({
                    "Criterion Name": ["Criterion 1", "Criterion 2", "Criterion 3"],
                    "Direction": ["benefit", "benefit", "cost"],
                    "Scale Type": ["ratio", "ratio", "ratio"],
                    "Unit": ["score", "score", "USD"],
                    "Description": ["", "", ""],
                })
            crit_df = st.data_editor(
                crit_df, num_rows="dynamic", use_container_width=True, key="crit_editor_step2",
                column_config={
                    "Direction": st.column_config.SelectboxColumn(
                        "Direction",
                        options=DIRECTION_OPTIONS,
                        help="Benefit = larger values preferred. Cost = smaller values preferred.",
                    ),
                    "Scale Type": st.column_config.SelectboxColumn("Scale Type", options=SCALE_OPTIONS),
                    "Unit": st.column_config.SelectboxColumn("Unit", options=UNIT_OPTIONS),
                    "Description": st.column_config.TextColumn("Description"),
                },
            )
            def _vft_to_dir(d): return d  # already benefit/cost
        st.markdown("</div>", unsafe_allow_html=True)

    crit_rows = []
    for _, r in crit_df.iterrows():
        name = str(r.get("Criterion Name", "")).strip()
        if not name:
            continue
        unit_val = str(r.get("Unit", "")).strip()
        if unit_val == "other":
            unit_val = None
        raw_dir = str(r.get("Direction", "benefit")).strip()
        crit_rows.append({
            "name": name,
            "direction": _vft_to_dir(raw_dir),
            "scale_type": str(r.get("Scale Type", "ratio")).strip(),
            "unit": unit_val,
            "description": str(r.get("Description", "")).strip() or None,
        })
    crit_names = list(dict.fromkeys([c["name"] for c in crit_rows]))

    st.markdown("")
    save_col, hint_col, next_col = st.columns([2, 3, 2])
    with save_col:
        if st.button("Save Alternatives & Criteria", type="primary", key="btn_save_alt_crit"):
            if not alt_names:
                st.error("Add at least 1 alternative.")
            elif not crit_rows:
                st.error("Add at least 1 criterion.")
            else:
                alt_repo.upsert_by_names(scenario_id, alt_names)
                crit_repo.upsert_rows(scenario_id, crit_rows)
                alt_repo.delete_missing(scenario_id, alt_names)
                crit_repo.delete_missing(scenario_id, crit_names)
                st.session_state["data_ready"] = False
                st.toast("Alternatives & Criteria saved.", icon="✅")
                st.rerun()
    with hint_col:
        st.caption("After saving, go to the **Performance Matrix** tab to enter values.")
    with next_col:
        st.caption("Then continue to matrix input.")
        st.button("Open Performance Matrix Tab", disabled=True, key="matrix_tab_hint")

# ─── Reload after possible save ───────────────────────────────────────────────
existing_alts = alt_repo.list_by_scenario(scenario_id)
existing_crit = crit_repo.list_by_scenario(scenario_id)
alt_names_db = [a["name"] for a in existing_alts]
crit_names_db = [c["name"] for c in existing_crit]

# ══════════════════════════════════════════════════════════════════════
# TAB 2: Performance Matrix
# ══════════════════════════════════════════════════════════════════════
with tab_matrix:
    if not alt_names_db or not crit_names_db:
        st.info("Save alternatives and criteria first (tab above) to unlock the matrix editor.")
    else:
        section_header("Performance Matrix", variant="accent")
        st.caption("Enter the raw values for each alternative–criterion combination.")

        # Direction legend
        if method_choice == "vft":
            legend_data = {c["name"]: ("↑ Maximize" if c["direction"] == "benefit" else "↓ Minimize") for c in existing_crit}
        else:
            legend_data = {c["name"]: ("↑ benefit" if c["direction"] == "benefit" else "↓ cost") for c in existing_crit}
        leg_row = " &nbsp;·&nbsp; ".join([f"**{n}**: {d}" for n, d in legend_data.items()])
        st.caption(f"Criterion directions: {leg_row}")

        existing_matrix = meas_repo.load_matrix_ui(scenario_id)
        if existing_matrix.empty:
            matrix_ui = pd.DataFrame(index=alt_names_db, columns=crit_names_db, dtype=float)
        else:
            matrix_ui = existing_matrix.reindex(index=alt_names_db, columns=crit_names_db)

        matrix_ui = st.data_editor(
            matrix_ui, use_container_width=True,
            key=f"matrix_editor_step2_{scenario_id}",
        )

        if st.button("Save Matrix", type="primary", key="btn_save_matrix"):
            if matrix_ui.isna().any().any():
                st.error("Matrix has missing cells — fill all values.")
            else:
                try:
                    matrix_numeric = matrix_ui.astype(float)
                    alt_map = alt_repo.upsert_by_names(scenario_id, alt_names_db)
                    crit_map = crit_repo.upsert_rows(scenario_id, [
                        {"name": c["name"], "direction": c["direction"],
                         "scale_type": c["scale_type"], "unit": c["unit"],
                         "description": c["description"]} for c in existing_crit
                    ])
                    meas_repo.replace_all_for_scenario(scenario_id, alt_map, crit_map, matrix_numeric)
                    st.session_state["data_ready"] = bool(st.session_state.get("preference_set_id"))
                    st.toast("Performance Matrix saved.", icon="✅")
                    st.rerun()
                except Exception as e:
                    st.error(f"Save failed: {e}")

# ══════════════════════════════════════════════════════════════════════
# TAB 3: Preference Sets & Gamified Weights
# ══════════════════════════════════════════════════════════════════════
with tab_prefs:
    if not alt_names_db or not crit_names_db:
        st.info("Save alternatives and criteria first.")
    else:
        section_header("Preference Sets", variant="accent")
        st.caption("A preference set holds one weighting scenario. Create multiple to compare stakeholder views.")

        with engine.begin() as conn:
            prefs = conn.execute(
                text("""
                    SELECT preference_set_id::text AS preference_set_id, name, type, status, created_at
                    FROM preference_sets WHERE scenario_id = :sid ORDER BY created_at DESC
                """),
                {"sid": scenario_id},
            ).mappings().all()
        prefs = [dict(p) for p in prefs]

        PREF_CREATE = "── Create new… ──"
        pref_ids = [p["preference_set_id"] for p in prefs]
        pref_id_to_name = {p["preference_set_id"]: p["name"] for p in prefs}
        pref_options = [PREF_CREATE] + pref_ids

        default_pref = st.session_state.get("preference_set_id") or (pref_ids[0] if pref_ids else PREF_CREATE)
        if default_pref not in pref_options:
            default_pref = PREF_CREATE

        picked_pref = st.multiselect(
            "Select preference set", options=pref_options, default=[default_pref], max_selections=1,
            format_func=lambda x: PREF_CREATE if x == PREF_CREATE else pref_id_to_name.get(x, x),
            key=f"pref_pick_step2_{scenario_id}",
        )
        selected_pref = picked_pref[0] if picked_pref else PREF_CREATE

        if selected_pref == PREF_CREATE:
            p1, p2 = st.columns(2)
            with p1:
                new_pref_name = st.text_input("New preference set name", value="Default Weights")
            with p2:
                st.caption("Name it e.g. 'Equal Weights', 'Cost-Focus', 'Quality-Focus'.")
            if st.button("Create Preference Set", type="primary", key="btn_create_pref"):
                pref_id = pref_repo.get_or_create_preference_set(
                    scenario_id=scenario_id,
                    name=new_pref_name.strip() or "Default Weights",
                    pref_type="direct",
                    created_by=user_name,
                )
                st.session_state["preference_set_id"] = pref_id
                st.session_state[f"force_equal_preset_{pref_id}"] = True
                st.toast(f"✅ Preference set '{new_pref_name}' created!", icon="⚖️")
                st.rerun()
        else:
            st.session_state["preference_set_id"] = selected_pref

        pref_id = st.session_state.get("preference_set_id")
        if not pref_id:
            st.info("Create or select a preference set above.")
            st.stop()

        st.divider()
        section_header("Weight Distribution", variant="sub")
        existing_weights = pref_repo.load_weights_by_criterion_name(pref_id)

        n_crits = len(crit_names_db)
        equal_preset = 1.0 / max(1, n_crits)

        def _has_meaningful_saved_weights(wmap: dict) -> bool:
            if not wmap:
                return False
            return any(float(v or 0) > 0 for v in wmap.values())

        # VFT: equal split by default when there are no saved weights (same baseline as TOPSIS)
        if method_choice == "vft":
            _vft_eq_key = f"vft_default_equal_weights_{pref_id}"
            if (
                not st.session_state.get(_vft_eq_key)
                and not _has_meaningful_saved_weights(existing_weights)
            ):
                st.session_state[f"force_equal_preset_{pref_id}"] = True
                st.session_state[_vft_eq_key] = True
        force_equal_preset = st.session_state.pop(f"force_equal_preset_{pref_id}", False)

        # ── Build weights from session state with two-way slider <-> number sync ──
        weights_by_name = {}
        criterion_colors = {
            cname: DISCRETE_PALETTE[i % len(DISCRETE_PALETTE)]
            for i, cname in enumerate(crit_names_db)
        }

        def _sync_weight_from_slider(base_key: str, slider_key: str, number_key: str):
            new_val = float(st.session_state.get(slider_key, 0.0))
            st.session_state[base_key] = new_val
            st.session_state[number_key] = new_val

        def _sync_weight_from_number(base_key: str, slider_key: str, number_key: str):
            new_val = max(0.0, min(1.0, float(st.session_state.get(number_key, 0.0))))
            st.session_state[base_key] = new_val
            st.session_state[slider_key] = new_val
            st.session_state[number_key] = new_val

        for cname in crit_names_db:
            cur_w = float(equal_preset if force_equal_preset else existing_weights.get(cname, equal_preset))
            base_key = f"w_{pref_id}_{cname}"
            slider_key = f"wslider_{pref_id}_{cname}"
            number_key = f"wnum_{pref_id}_{cname}"
            init_val = min(max(cur_w, 0.0), 1.0)

            if force_equal_preset or base_key not in st.session_state:
                st.session_state[base_key] = init_val
            if force_equal_preset or slider_key not in st.session_state:
                st.session_state[slider_key] = float(st.session_state[base_key])
            if force_equal_preset or number_key not in st.session_state:
                st.session_state[number_key] = float(st.session_state[base_key])

        preset_col, normalize_col = st.columns([2, 2])
        with preset_col:
            if st.button("Reset To Equal Preset", key=f"btn_equal_preset_{pref_id}"):
                for cname in crit_names_db:
                    st.session_state[f"w_{pref_id}_{cname}"] = equal_preset
                    st.session_state[f"wslider_{pref_id}_{cname}"] = equal_preset
                    st.session_state[f"wnum_{pref_id}_{cname}"] = equal_preset
                st.toast("Preset applied: all criteria set to equal weights.", icon="✅")
                st.rerun()
        with normalize_col:
            auto_normalize = st.checkbox("Auto-normalize to sum = 1", value=True, key=f"autonorm_{pref_id}")

        wt_left, wt_right = st.columns([3, 2], gap="large")

        with wt_left:
            st.caption("Drag sliders or type exact values. They stay synced in real time.")

            for cname in crit_names_db:
                base_key = f"w_{pref_id}_{cname}"
                slider_key = f"wslider_{pref_id}_{cname}"
                number_key = f"wnum_{pref_id}_{cname}"
                crit_dir = next((c["direction"] for c in existing_crit if c["name"] == cname), "benefit")
                dir_icon = "↑" if crit_dir == "benefit" else "↓"
                chip_color = criterion_colors[cname]

                col_label, col_slider, col_num = st.columns([2, 5, 2])
                with col_label:
                    st.markdown(
                        f"<div style='padding-top:8px;display:flex;align-items:center;gap:8px'>"
                        f"<span style='display:inline-block;width:10px;height:10px;border-radius:999px;background:{chip_color}'></span>"
                        f"<span>{dir_icon} <strong>{cname}</strong></span>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )
                with col_slider:
                    st.slider(
                        cname,
                        min_value=0.0,
                        max_value=1.0,
                        value=float(st.session_state[slider_key]),
                        step=0.01,
                        label_visibility="collapsed",
                        key=slider_key,
                        on_change=_sync_weight_from_slider,
                        args=(base_key, slider_key, number_key),
                    )
                with col_num:
                    st.number_input(
                        " ",
                        min_value=0.0,
                        max_value=1.0,
                        value=float(st.session_state[number_key]),
                        step=0.01,
                        format="%.3f",
                        key=number_key,
                        label_visibility="hidden",
                        on_change=_sync_weight_from_number,
                        args=(base_key, slider_key, number_key),
                    )

                weights_by_name[cname] = float(st.session_state[base_key])

        with wt_right:
            w_arr = np.array([float(weights_by_name.get(c, 0.0)) for c in crit_names_db])
            w_sum = w_arr.sum()
            if auto_normalize and w_sum > 0:
                w_display = w_arr / w_sum
            else:
                w_display = w_arr

            # ── Donut chart ──
            fig = go.Figure(go.Pie(
                labels=crit_names_db,
                values=w_display,
                hole=0.55,
                textinfo="percent",
                textfont_size=13,
                hovertemplate="<b>%{label}</b><br>Weight: %{value:.3f}<br>Share: %{percent}<extra></extra>",
                marker=dict(
                    colors=[criterion_colors[cname] for cname in crit_names_db],
                    line=dict(color="white", width=2),
                ),
                pull=[0.04] * n_crits,
                sort=False,
            ))
            fig.update_layout(
                annotations=[dict(text=f"{n_crits}<br>criteria", x=0.5, y=0.5, font_size=15,
                                  showarrow=False, font_color="#2d3748")],
                margin=dict(l=10, r=10, t=10, b=10),
                height=280,
                width=460,
                showlegend=False,
                paper_bgcolor="rgba(0,0,0,0)",
            )
            st.plotly_chart(fig, use_container_width=False, key=f"pie_{pref_id}")

            # ── Ranked list with color legend matching the donut chart ──
            w_pairs = sorted(zip(crit_names_db, w_display), key=lambda x: x[1], reverse=True)
            medal = ["#1", "#2", "#3"]
            st.markdown("<div style='margin-top:4px'>", unsafe_allow_html=True)
            for i, (cname, wval) in enumerate(w_pairs):
                icon = medal[i] if i < 3 else f"#{i+1}"
                bar_pct = int(wval * 100)
                color = criterion_colors[cname]
                st.markdown(
                    f"<div style='display:flex;align-items:center;gap:8px;margin-bottom:8px'>"
                    f"<span style='font-size:1.1rem;min-width:28px'>{icon}</span>"
                    f"<div style='flex:1'>"
                    f"<div style='display:flex;justify-content:space-between;align-items:center;gap:8px'>"
                    f"<span style='display:flex;align-items:center;gap:8px;font-weight:600;font-size:0.9rem'>"
                    f"<span style='display:inline-block;width:10px;height:10px;border-radius:999px;background:{color}'></span>"
                    f"<span>{cname}</span>"
                    f"</span>"
                    f"<span style='font-size:0.85rem;color:#4a5568'>{wval:.3f}</span>"
                    f"</div>"
                    f"<div style='background:#e2e8f0;border-radius:6px;height:8px;margin-top:4px'>"
                    f"<div style='background:{color};width:{bar_pct}%;height:8px;"
                    f"border-radius:6px;transition:width 0.4s ease'></div>"
                    f"</div></div></div>",
                    unsafe_allow_html=True,
                )
            sum_color = "#2A9D8F" if abs(w_sum - 1.0) < 0.001 or auto_normalize else "#1E3A5F"
            st.markdown(
                f"<div style='text-align:right;margin-top:8px;font-weight:700;color:{sum_color}'>"
                f"Σ = {w_sum:.3f} {'✓' if abs(w_sum - 1.0) < 0.001 else '(will normalize)'}</div>",
                unsafe_allow_html=True,
            )
            st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("")
        save_w_col, tip_col = st.columns([2, 4])
        with save_w_col:
            if st.button("Save Weights", type="primary", key=f"btn_save_weights_{pref_id}"):
                w_vals = np.array([float(weights_by_name.get(c, 0.0)) for c in crit_names_db])
                if auto_normalize and w_vals.sum() > 0:
                    w_vals = w_vals / w_vals.sum()
                weights_final = {crit_names_db[i]: float(w_vals[i]) for i in range(len(crit_names_db))}

                alt_map = alt_repo.upsert_by_names(scenario_id, alt_names_db)
                crit_map = crit_repo.upsert_rows(scenario_id, [
                    {"name": c["name"], "direction": c["direction"],
                     "scale_type": c["scale_type"], "unit": c["unit"],
                     "description": c["description"]} for c in existing_crit
                ])
                pref_repo.replace_weights(pref_id, crit_map, weights_final)

                mat = meas_repo.load_matrix_ui(scenario_id)
                if not mat.empty and not mat.isna().any().any():
                    st.session_state["data_ready"] = True
                st.toast("Weights saved. You can proceed to the next step.", icon="✅")
                st.rerun()
        with tip_col:
            st.caption("💡 Tip: Create multiple preference sets to model different stakeholder perspectives.")
