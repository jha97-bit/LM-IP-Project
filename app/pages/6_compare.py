import bootstrap  # noqa: F401

import uuid
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import streamlit as st
from sqlalchemy import text
import plotly.express as px
import plotly.graph_objects as go

from persistence.engine import get_engine
from persistence.repositories.run_repo import RunRepo
from persistence.repositories.result_repo import ResultRepo
from persistence.repositories.topsis_read_repo import TopsisReadRepo
from persistence.repositories.preference_repo import PreferenceRepo
from services.scenario_service import ScenarioService
from services.topsis_service import TopsisService

st.title("Step 6: Compare (Preference Sets)")

engine = get_engine()
run_repo = RunRepo(engine)
result_repo = ResultRepo(engine)
topsis_read_repo = TopsisReadRepo(engine)
pref_repo = PreferenceRepo(engine)
scenario_service = ScenarioService(engine)
topsis_service = TopsisService(engine)

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
    if st.button("Back: Step 5 (History)"):
        st.switch_page("pages/5_history.py")
with nav_right:
    st.button("Next", disabled=True)

st.divider()

# ----------------------------
# Helpers
# ----------------------------
def searchable_single_select(
    label: str,
    options: list[str],
    default_value: str | None,
    format_func,
    key: str,
) -> str:
    if not options:
        return ""
    if default_value not in options:
        default_value = options[0]
    picked = st.multiselect(
        label,
        options=options,
        default=[default_value] if default_value else [options[0]],
        max_selections=1,
        format_func=format_func,
        key=key,
    )
    return picked[0] if picked else options[0]


def load_scenario_decision_id(sid: str) -> str | None:
    with engine.begin() as conn:
        row = conn.execute(
            text(
                """
                SELECT decision_id::text AS decision_id
                FROM scenarios
                WHERE scenario_id = :sid
                """
            ),
            {"sid": sid},
        ).mappings().first()
    return row["decision_id"] if row else None


def load_scenarios_for_decision(did: str) -> list[dict]:
    with engine.begin() as conn:
        rows = conn.execute(
            text(
                """
                SELECT scenario_id::text AS scenario_id, name, created_at, created_by
                FROM scenarios
                WHERE decision_id = :did
                ORDER BY created_at ASC
                """
            ),
            {"did": did},
        ).mappings().all()
    return [dict(r) for r in rows]


def load_preference_sets_for_scenario(sid: str) -> list[dict]:
    with engine.begin() as conn:
        rows = conn.execute(
            text(
                """
                SELECT preference_set_id::text AS preference_set_id, name, created_at
                FROM preference_sets
                WHERE scenario_id = :sid
                ORDER BY created_at DESC
                """
            ),
            {"sid": sid},
        ).mappings().all()
    return [dict(r) for r in rows]


def list_topsis_runs_for_scenario_and_pref(sid: str, pref_id: str) -> list[dict]:
    with engine.begin() as conn:
        rows = conn.execute(
            text(
                """
                SELECT run_id::text AS run_id, executed_at, executed_by,
                       preference_set_id::text AS preference_set_id, method
                FROM runs
                WHERE scenario_id = :sid
                  AND preference_set_id = :pid
                  AND method = 'topsis'
                ORDER BY executed_at DESC
                LIMIT 200
                """
            ),
            {"sid": sid, "pid": pref_id},
        ).mappings().all()
    return [dict(r) for r in rows]


def label_run(r: dict) -> str:
    by = (r.get("executed_by") or "").strip()
    by_part = f" | {by}" if by else ""
    return f"{r.get('executed_at')}{by_part} | {r['run_id'][:8]}…"


def get_scores(run_id: str) -> pd.DataFrame:
    return pd.DataFrame(result_repo.get_scores_with_names(run_id))


def get_distances(run_id: str) -> pd.DataFrame:
    df = topsis_read_repo.get_distances(run_id)
    if df is None:
        return pd.DataFrame()
    return df


def get_ideals(run_id: str) -> pd.DataFrame:
    df = topsis_read_repo.get_ideals(run_id)
    if df is None:
        return pd.DataFrame()
    return df


def get_matrix(run_id: str, matrix_type: str) -> pd.DataFrame:
    df = topsis_read_repo.get_matrix(run_id, matrix_type)
    if df is None:
        return pd.DataFrame()
    return df


def _normalize_alt_col(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return df
    df2 = df.copy()
    if "alternative" in df2.columns and "alternative_name" not in df2.columns:
        df2 = df2.rename(columns={"alternative": "alternative_name"})
    return df2


def _ensure_cache_defaults():
    st.session_state.setdefault("cmp_ready", False)
    st.session_state.setdefault("cmp_payload", None)
    st.session_state.setdefault("sb_ready", False)
    st.session_state.setdefault("sb_payload", {})  # IMPORTANT: never None


_ensure_cache_defaults()


def load_criteria_meta(sid: str) -> pd.DataFrame:
    with engine.begin() as conn:
        rows = conn.execute(
            text(
                """
                SELECT criterion_id::text AS criterion_id, name, direction, scale_type, unit, description
                FROM criteria
                WHERE scenario_id = :sid
                ORDER BY created_at ASC
                """
            ),
            {"sid": sid},
        ).mappings().all()
    df = pd.DataFrame([dict(r) for r in rows])
    if df.empty:
        return df
    df["direction"] = df["direction"].fillna("benefit")
    df["unit"] = df["unit"].fillna("")
    df["description"] = df["description"].fillna("")
    return df


def topsis_from_normalized(
    norm_df: pd.DataFrame,
    crit_meta: pd.DataFrame,
    weights_by_name: dict[str, float],
) -> dict:
    if norm_df is None or norm_df.empty:
        return {
            "weighted_df": pd.DataFrame(),
            "ideals_df": pd.DataFrame(),
            "dist_df": pd.DataFrame(),
            "ranking_df": pd.DataFrame(),
            "contrib_long": pd.DataFrame(),
            "weights_series": pd.Series(dtype=float),
        }

    crits = list(norm_df.columns)
    w = np.array([float(weights_by_name.get(c, 0.0)) for c in crits], dtype=float)
    if float(w.sum()) <= 0:
        w = np.ones(len(crits), dtype=float) / max(1, len(crits))
    else:
        w = w / float(w.sum())

    w_series = pd.Series(w, index=crits)

    weighted_df = norm_df.astype(float).mul(w_series, axis=1)

    meta_by_name = {}
    if crit_meta is not None and not crit_meta.empty and "name" in crit_meta.columns:
        meta_by_name = crit_meta.set_index("name")[["direction"]].to_dict(orient="index")

    pos_ideal = {}
    neg_ideal = {}
    for c in crits:
        direction = (meta_by_name.get(c, {}).get("direction", "benefit") or "benefit").strip().lower()
        col = weighted_df[c].astype(float)
        if direction == "cost":
            pos_ideal[c] = float(col.min())
            neg_ideal[c] = float(col.max())
        else:
            pos_ideal[c] = float(col.max())
            neg_ideal[c] = float(col.min())

    ideals_df = pd.DataFrame(
        {
            "criterion": crits,
            "pos_ideal": [pos_ideal[c] for c in crits],
            "neg_ideal": [neg_ideal[c] for c in crits],
            "weight": [float(w_series[c]) for c in crits],
        }
    )

    pos_vec = np.array([pos_ideal[c] for c in crits], dtype=float)
    neg_vec = np.array([neg_ideal[c] for c in crits], dtype=float)
    X = weighted_df[crits].astype(float).values

    s_pos = np.sqrt(((X - pos_vec) ** 2).sum(axis=1))
    s_neg = np.sqrt(((X - neg_vec) ** 2).sum(axis=1))
    denom = s_pos + s_neg
    denom[denom == 0] = 1e-12
    c_star = s_neg / denom

    dist_df = pd.DataFrame(
        {
            "alternative": list(weighted_df.index),
            "s_pos": s_pos,
            "s_neg": s_neg,
            "c_star": c_star,
        }
    )

    ranking_df = dist_df.copy()
    ranking_df = ranking_df.sort_values("c_star", ascending=False).reset_index(drop=True)
    ranking_df["rank"] = np.arange(1, len(ranking_df) + 1)
    ranking_df = ranking_df.rename(columns={"alternative": "alternative_name", "c_star": "score"})
    ranking_df = ranking_df[["alternative_name", "score", "rank"]]

    wd_reset = weighted_df.reset_index()

# The first column after reset_index is the index column, but its name can vary:
# - "index" (no index name)
# - "alternative" (if index.name == "alternative")
# - something else if you set it earlier
    first_col = wd_reset.columns[0]
    wd_reset = wd_reset.rename(columns={first_col: "alternative_name"})

    contrib_long = wd_reset.melt(
        id_vars=["alternative_name"],
        var_name="criterion",
        value_name="contribution",
    )
    contrib_long["weight"] = contrib_long["criterion"].map(lambda c: float(w_series.get(c, 0.0)))

    return {
        "weighted_df": weighted_df,
        "ideals_df": ideals_df,
        "dist_df": dist_df,
        "ranking_df": ranking_df,
        "contrib_long": contrib_long,
        "weights_series": w_series,
    }


def make_unique_pref_name(sid: str, base_name: str) -> str:
    base = (base_name or "").strip() or "Sandbox Weights"

    with engine.begin() as conn:
        existing = conn.execute(
            text(
                """
                SELECT name
                FROM preference_sets
                WHERE scenario_id = :sid
                """
            ),
            {"sid": sid},
        ).fetchall()
    existing_names = {r[0] for r in existing}

    if base not in existing_names:
        return base

    i = 2
    while True:
        cand = f"{base} ({i})"
        if cand not in existing_names:
            return cand
        i += 1


def insert_preference_set_and_weights(
    sid: str,
    pref_name: str,
    weights_by_criterion_name: dict[str, float],
    created_by: str,
) -> str:
    pref_id = str(uuid.uuid4())
    created_at = datetime.now(timezone.utc)

    # Use the DB-allowed value for "type". Your earlier error shows "direct" is valid.
    ptype = "direct"
    status = "active"

    crit_rows = load_criteria_meta(sid)
    if crit_rows is None or crit_rows.empty:
        raise RuntimeError("No criteria found for this scenario. Save criteria in Step 2 first.")

    crit_map = {row["name"]: row["criterion_id"] for _, row in crit_rows.iterrows()}

    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO preference_sets (
                    preference_set_id, scenario_id, type, name, status, created_at, created_by
                )
                VALUES (
                    :pid, :sid, :ptype, :name, :status, :created_at, :created_by
                )
                """
            ),
            {
                "pid": pref_id,
                "sid": sid,
                "ptype": ptype,
                "name": pref_name,
                "status": status,
                "created_at": created_at,
                "created_by": created_by or "",
            },
        )

        for cname, w in weights_by_criterion_name.items():
            cid = crit_map.get(cname)
            if not cid:
                continue
            conn.execute(
                text(
                    """
                    INSERT INTO criterion_weights (
                        preference_set_id, criterion_id, weight, created_at
                    )
                    VALUES (
                        :pid, :cid, :w, :created_at
                    )
                    ON CONFLICT (preference_set_id, criterion_id)
                    DO UPDATE SET weight = EXCLUDED.weight
                    """
                ),
                {"pid": pref_id, "cid": cid, "w": float(w), "created_at": created_at},
            )

    return pref_id


# ----------------------------
# Scenario picker (within current decision)
# ----------------------------
decision_id = load_scenario_decision_id(scenario_id)
if not decision_id:
    st.error("Could not find decision for selected scenario.")
    st.stop()

scenarios = load_scenarios_for_decision(decision_id)
scen_ids = [s["scenario_id"] for s in scenarios]
scen_id_to_obj = {s["scenario_id"]: s for s in scenarios}


def scen_label(sid: str) -> str:
    s = scen_id_to_obj[sid]
    return f"{s['name']} ({sid[:8]}…)"


picked_scenario = searchable_single_select(
    "Scenario",
    options=scen_ids,
    default_value=scenario_id,
    format_func=scen_label,
    key="cmp_pref_scenario_pick",
)
st.session_state["scenario_id"] = picked_scenario

st.divider()

# ============================================================
# SANDBOX (Weights sliders + live recompute)  [TOP SECTION]
# ============================================================
st.subheader("Weight Sandbox (live)")

prefs_for_sb = load_preference_sets_for_scenario(picked_scenario)
if not prefs_for_sb:
    st.info("No preference sets found. Create one in Step 2 first.")
    st.stop()

pref_ids_sb = [p["preference_set_id"] for p in prefs_for_sb]
pref_id_to_name_sb = {p["preference_set_id"]: p["name"] for p in prefs_for_sb}

default_pref_sb = st.session_state.get("preference_set_id") or pref_ids_sb[0]
picked_pref_sb = searchable_single_select(
    "Baseline preference set",
    options=pref_ids_sb,
    default_value=default_pref_sb,
    format_func=lambda x: pref_id_to_name_sb.get(x, x),
    key="sb_baseline_pref_pick",
)
st.session_state["preference_set_id"] = picked_pref_sb

runs_sb = list_topsis_runs_for_scenario_and_pref(picked_scenario, picked_pref_sb)
if not runs_sb:
    st.warning("No TOPSIS run found for the chosen baseline preference set. Run TOPSIS in Step 3 first.")
    st.stop()

baseline_run_id = runs_sb[0]["run_id"]
st.caption(f"Baseline run: {baseline_run_id[:8]}… (latest TOPSIS run for selected preference set)")

sb_cache_key = f"sb_key::{picked_scenario}::{picked_pref_sb}::{baseline_run_id}"

# FIX: session_state["sb_payload"] can be None from old runs. Guard it.
_sb_payload = st.session_state.get("sb_payload")
if not isinstance(_sb_payload, dict):
    _sb_payload = {}
    st.session_state["sb_payload"] = _sb_payload

if _sb_payload.get("sb_cache_key") != sb_cache_key:
    crit_meta = load_criteria_meta(picked_scenario)

    norm_df_base = get_matrix(baseline_run_id, "normalized")
    if norm_df_base is None or norm_df_base.empty:
        st.warning("Baseline run has no normalized matrix saved. Re-run TOPSIS in Step 3.")
        st.stop()

    weights_map_base = pref_repo.load_weights_by_criterion_name(picked_pref_sb)
    base_calc = topsis_from_normalized(norm_df_base, crit_meta, weights_map_base)

    st.session_state["sb_ready"] = True
    st.session_state["sb_payload"] = {
        "sb_cache_key": sb_cache_key,
        "scenario_id": picked_scenario,
        "baseline_pref_id": picked_pref_sb,
        "baseline_pref_name": pref_id_to_name_sb.get(picked_pref_sb, picked_pref_sb),
        "baseline_run_id": baseline_run_id,
        "crit_meta": crit_meta,
        "norm_df_base": norm_df_base,
        "weights_base": weights_map_base,
        "base_calc": base_calc,
    }

sb = st.session_state.get("sb_payload") if st.session_state.get("sb_ready") else None
if not isinstance(sb, dict) or not sb:
    st.stop()

crit_meta = sb["crit_meta"]
norm_df_base = sb["norm_df_base"]
weights_base = sb["weights_base"]
base_calc = sb["base_calc"]

crits = list(norm_df_base.columns)
weights_base_vec = np.array([float(weights_base.get(c, 0.0)) for c in crits], dtype=float)
if float(weights_base_vec.sum()) <= 0:
    weights_base_vec = np.ones(len(crits), dtype=float) / max(1, len(crits))
else:
    weights_base_vec = weights_base_vec / float(weights_base_vec.sum())

st.markdown("### Adjust weights")
st.caption("Move sliders, then charts update immediately. Use normalize to keep weights summing to 1.")

sb_cols = st.columns(min(5, len(crits)))
weights_sandbox_raw = {}
for i, c in enumerate(crits):
    with sb_cols[i % len(sb_cols)]:
        weights_sandbox_raw[c] = st.slider(
            c,
            min_value=0.0,
            max_value=1.0,
            value=float(weights_base_vec[i]),
            step=0.01,
            key=f"sb_w_{sb_cache_key}_{c}",
        )

auto_norm = st.checkbox("Auto-normalize sandbox weights to sum to 1", value=True, key=f"sb_auton_{sb_cache_key}")
w_sandbox = np.array([float(weights_sandbox_raw[c]) for c in crits], dtype=float)
if auto_norm:
    s = float(w_sandbox.sum())
    if s <= 0:
        w_sandbox = np.ones(len(crits), dtype=float) / max(1, len(crits))
    else:
        w_sandbox = w_sandbox / s
weights_sandbox = {crits[i]: float(w_sandbox[i]) for i in range(len(crits))}

sandbox_calc = topsis_from_normalized(norm_df_base, crit_meta, weights_sandbox)

st.markdown("### Live impact")

colA, colB = st.columns([1, 1])

with colA:
    st.markdown("**Ranking shift** (baseline vs sandbox)")
    rank_base = base_calc["ranking_df"].copy()
    rank_sand = sandbox_calc["ranking_df"].copy()

    if not rank_base.empty and not rank_sand.empty:
        rb = rank_base.rename(columns={"score": "score_base", "rank": "rank_base"})
        rs = rank_sand.rename(columns={"score": "score_sandbox", "rank": "rank_sandbox"})
        merge = rb.merge(rs, on="alternative_name", how="outer")
        merge["rank_delta"] = merge["rank_sandbox"] - merge["rank_base"]
        merge["score_delta"] = merge["score_sandbox"] - merge["score_base"]
        merge = merge.sort_values("rank_base", ascending=True)

        fig_delta = px.bar(
            merge,
            x="alternative_name",
            y="score_delta",
            hover_data={
                "rank_base": True,
                "rank_sandbox": True,
                "score_base": ":.6f",
                "score_sandbox": ":.6f",
            },
            labels={"alternative_name": "Alternative", "score_delta": "Sandbox score change (C*)"},
            title="Score change (Sandbox minus Baseline)",
        )
        st.plotly_chart(fig_delta, use_container_width=True)
    else:
        st.info("Missing ranking data to show deltas.")

with colB:
    st.markdown("**Distance view** (sandbox)")
    dist_s = sandbox_calc["dist_df"]
    if dist_s is not None and not dist_s.empty:
        fig_dist = px.scatter(
            dist_s,
            x="s_pos",
            y="s_neg",
            text="alternative",
            hover_data={"c_star": ":.6f", "s_pos": ":.6f", "s_neg": ":.6f"},
            labels={"s_pos": "S+ (to PIS)", "s_neg": "S- (to NIS)"},
            title="Sandbox: S+ vs S-",
        )
        fig_dist.update_traces(textposition="top center")
        st.plotly_chart(fig_dist, use_container_width=True)
    else:
        st.info("Missing distances for sandbox.")

st.divider()

st.markdown("### Score composition (criterion contributions)")

# --- Score composition (criterion contributions) ---

contrib_b = base_calc["contrib_long"]
contrib_s = sandbox_calc["contrib_long"]

if contrib_b is None or contrib_b.empty or contrib_s is None or contrib_s.empty:
    st.info("Missing contribution data.")
else:
    alt_all = sorted(list(contrib_b["alternative_name"].unique()))
    default_alts = alt_all[:6]

    picked_alts_comp = st.multiselect(
        "Alternatives for composition (up to 6)",
        options=alt_all,
        default=default_alts,
        max_selections=6,
        key=f"sb_comp_alts_{sb_cache_key}",
    )

    if picked_alts_comp:
        cb = contrib_b[contrib_b["alternative_name"].isin(picked_alts_comp)].copy()
        cs = contrib_s[contrib_s["alternative_name"].isin(picked_alts_comp)].copy()

        # Make sure ordering is stable
        cb["alternative_name"] = pd.Categorical(cb["alternative_name"], categories=picked_alts_comp, ordered=True)
        cs["alternative_name"] = pd.Categorical(cs["alternative_name"], categories=picked_alts_comp, ordered=True)

        fig_comp = go.Figure()

        # Two stacked bars per alternative using offsetgroup:
        # - Baseline stack is offsetgroup="Baseline"
        # - Sandbox stack is offsetgroup="Sandbox"
        for c in crits:
            sub_b = cb[cb["criterion"] == c]
            sub_s = cs[cs["criterion"] == c]

            fig_comp.add_trace(
                go.Bar(
                    x=sub_b["alternative_name"],
                    y=sub_b["contribution"],
                    name=f"{c} | Baseline",
                    offsetgroup="Baseline",
                    legendgroup=c,
                    legendgrouptitle_text=c,
                    opacity=0.55,
                )
            )
            fig_comp.add_trace(
                go.Bar(
                    x=sub_s["alternative_name"],
                    y=sub_s["contribution"],
                    name=f"{c} | Sandbox",
                    offsetgroup="Sandbox",
                    legendgroup=c,
                    opacity=0.95,
                )
            )

        fig_comp.update_layout(
            barmode="relative",  # stacks within each offsetgroup
            title="Stacked contributions per alternative: Baseline vs Sandbox",
            xaxis_title="Alternative",
            yaxis_title="Sum of weighted normalized contributions",
            height=650,
            legend=dict(orientation="h"),
            margin=dict(l=10, r=10, t=70, b=10),
        )

        st.plotly_chart(fig_comp, use_container_width=True)
    else:
        st.info("Pick at least 1 alternative.")

st.divider()

st.markdown("### Radar comparison (Baseline vs Sandbox)")

weighted_base = base_calc["weighted_df"]
weighted_sand = sandbox_calc["weighted_df"]

if (
    weighted_base is not None
    and not weighted_base.empty
    and weighted_sand is not None
    and not weighted_sand.empty
):
    alt_options = list(weighted_base.index)

    base_rank_df = base_calc.get("ranking_df", pd.DataFrame())
    default_alts = []
    if base_rank_df is not None and not base_rank_df.empty and "alternative_name" in base_rank_df.columns:
        default_alts = base_rank_df.sort_values("rank")["alternative_name"].tolist()[:3]
    if not default_alts:
        default_alts = alt_options[:3]

    picked_alts = st.multiselect(
        "Alternatives (pick 1 to 5)",
        options=alt_options,
        default=[a for a in default_alts if a in alt_options],
        max_selections=5,
        key=f"sb_radar_alts_{sb_cache_key}",
    )

    if picked_alts:
        radar_scale = st.selectbox(
            "Radar scaling",
            options=[
                "Normalize 0..1 per criterion (recommended)",
                "Raw weighted values (can be hard to read)",
            ],
            index=0,
            key=f"sb_radar_scale_{sb_cache_key}",
        )

        if radar_scale.startswith("Normalize"):
            vals_all = []
            for a in picked_alts:
                vals_all.append(weighted_base.loc[a, crits].astype(float).values)
                vals_all.append(weighted_sand.loc[a, crits].astype(float).values)
            combined = np.vstack(vals_all)
            cmin = combined.min(axis=0)
            cmax = combined.max(axis=0)
            denom = (cmax - cmin)
            denom[denom == 0] = 1.0

            def _scale(v: np.ndarray) -> np.ndarray:
                return (v - cmin) / denom

            radial_range = [0, 1]
            axis_title = "Scaled weighted value (0..1)"
        else:

            def _scale(v: np.ndarray) -> np.ndarray:
                return v

            combined = []
            for a in picked_alts:
                combined.append(weighted_base.loc[a, crits].astype(float).values)
                combined.append(weighted_sand.loc[a, crits].astype(float).values)
            combined = np.vstack(combined)
            mn = float(np.nanmin(combined))
            mx = float(np.nanmax(combined))
            pad = (mx - mn) * 0.1 if mx > mn else 0.1
            radial_range = [mn - pad, mx + pad]
            axis_title = "Weighted value"

        fig_radar_multi = go.Figure()

        for alt in picked_alts:
            vb = weighted_base.loc[alt, crits].astype(float).values
            vs = weighted_sand.loc[alt, crits].astype(float).values
            vb_s = _scale(vb)
            vs_s = _scale(vs)

            fig_radar_multi.add_trace(
                go.Scatterpolar(
                    r=vb_s,
                    theta=crits,
                    fill="toself",
                    name=f"{alt} | Baseline",
                    opacity=0.35,
                    hovertemplate="Trace=%{fullData.name}<br>Criterion=%{theta}<br>Value=%{r:.4f}<extra></extra>",
                )
            )
            fig_radar_multi.add_trace(
                go.Scatterpolar(
                    r=vs_s,
                    theta=crits,
                    fill="toself",
                    name=f"{alt} | Sandbox",
                    opacity=0.55,
                    hovertemplate="Trace=%{fullData.name}<br>Criterion=%{theta}<br>Value=%{r:.4f}<extra></extra>",
                )
            )

        fig_radar_multi.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=radial_range,
                    title=axis_title,
                )
            ),
            title="Radar: Baseline vs Sandbox across chosen alternatives",
            height=650,
            margin=dict(l=10, r=10, t=70, b=10),
            legend=dict(orientation="h"),
        )
        st.plotly_chart(fig_radar_multi, use_container_width=True)
    else:
        st.info("Pick at least 1 alternative to render radar.")
else:
    st.info("Radar view needs weighted matrices.")

st.divider()

st.markdown("### Save sandbox weights")

save_name_default = f"Sandbox {datetime.now().strftime('%Y-%m-%d %H:%M')}"
save_name = st.text_input(
    "Preference set name to save",
    value=save_name_default,
    key=f"sb_save_name_{sb_cache_key}",
)

save_col1, save_col2 = st.columns(2)

with save_col1:
    if st.button("Save preference set", type="secondary", key=f"sb_save_pref_{sb_cache_key}"):
        try:
            unique_name = make_unique_pref_name(picked_scenario, save_name)
            new_pref_id = insert_preference_set_and_weights(
                sid=picked_scenario,
                pref_name=unique_name,
                weights_by_criterion_name=weights_sandbox,
                created_by=user_name,
            )
            st.success(f"Saved preference set: {unique_name} ({new_pref_id[:8]}…)")
        except Exception as e:
            st.error(str(e))

with save_col2:
    if st.button("Save and run model", type="primary", key=f"sb_save_and_run_{sb_cache_key}"):
        try:
            unique_name = make_unique_pref_name(picked_scenario, save_name)
            new_pref_id = insert_preference_set_and_weights(
                sid=picked_scenario,
                pref_name=unique_name,
                weights_by_criterion_name=weights_sandbox,
                created_by=user_name,
            )

            data = scenario_service.load(picked_scenario, new_pref_id)
            ok, issues = scenario_service.validate(data)
            if not ok:
                st.error("Scenario not runnable with these weights.")
                for msg in issues:
                    st.error(msg)
                st.stop()

            run_id = topsis_service.run_and_persist(
                scenario_id=picked_scenario,
                preference_set_id=new_pref_id,
                executed_by=user_name,
                data=data,
            )
            st.session_state["last_run_id"] = run_id
            st.success(f"Saved preference set and created run: {run_id[:8]}…")
        except Exception as e:
            st.error(str(e))

st.divider()

# ============================================================
# COMPARE (independent of sandbox)
# ============================================================
st.subheader("Choose Preference Sets to Compare")
st.caption("This section works even if you do not use the sandbox above. Pick 2 to 5 preference sets and click Compare.")

prefs = load_preference_sets_for_scenario(picked_scenario)
if len(prefs) < 2:
    st.info("You need at least 2 preference sets in this scenario to compare. Create more in Step 2.")
    st.stop()

pref_ids = [p["preference_set_id"] for p in prefs]
pref_id_to_name = {p["preference_set_id"]: p["name"] for p in prefs}

default_pref = st.session_state.get("preference_set_id")
defaults: list[str] = []
if default_pref in pref_ids:
    defaults.append(default_pref)
for pid in pref_ids:
    if len(defaults) >= 2:
        break
    if pid not in defaults:
        defaults.append(pid)

selected_prefs = st.multiselect(
    "Preference sets (2 to 5)",
    options=pref_ids,
    default=defaults,
    max_selections=5,
    format_func=lambda x: pref_id_to_name.get(x, x),
    key=f"cmp_pref_sets_{picked_scenario}",
)

if len(selected_prefs) < 2:
    st.warning("Pick at least 2 preference sets to compare.")
    st.stop()

use_latest_runs = st.checkbox("Use latest TOPSIS run for each preference set", value=True, key="cmp_use_latest")

pref_to_run_id: dict[str, str] = {}
missing_runs: list[str] = []

for pid in selected_prefs:
    runs = list_topsis_runs_for_scenario_and_pref(picked_scenario, pid)
    pref_name = pref_id_to_name.get(pid, pid)

    if not runs:
        missing_runs.append(pref_name)
        continue

    if use_latest_runs:
        pref_to_run_id[pid] = runs[0]["run_id"]
    else:
        labels = [label_run(r) for r in runs]
        label_to_id = {labels[i]: runs[i]["run_id"] for i in range(len(labels))}
        chosen = st.selectbox(
            f"Run for {pref_name}",
            options=labels,
            index=0,
            key=f"cmp_run_pick_{picked_scenario}_{pid}",
        )
        pref_to_run_id[pid] = label_to_id[chosen]

if missing_runs:
    st.warning(
        "Some preference sets have no TOPSIS runs yet: "
        + ", ".join(missing_runs)
        + ". Run TOPSIS in Step 3 for those sets."
    )
    st.stop()

st.divider()

st.subheader("Compare")

colA, colB, colC = st.columns([1, 1, 2])
with colA:
    order_mode = st.selectbox(
        "Alternative order",
        options=["By name", "By rank of first preference set"],
        index=1,
        key="cmp_order_mode",
    )
with colB:
    st.checkbox("Show rank chart", value=True, key="cmp_show_rank_chart")
with colC:
    st.caption("Tip: hover any point or bar to see set name, score, rank, run_id.")

do_compare = st.button("Compare", type="primary", key="cmp_do_compare")

if do_compare:
    rows = []
    dist_rows = []
    ideals_by_pref: dict[str, pd.DataFrame] = {}
    weighted_by_pref: dict[str, pd.DataFrame] = {}
    normalized_by_pref: dict[str, pd.DataFrame] = {}

    for pid in selected_prefs:
        run_id = pref_to_run_id[pid]
        pref_name = pref_id_to_name.get(pid, pid)

        df = _normalize_alt_col(get_scores(run_id))
        if df is None or df.empty:
            continue

        df = df.copy()
        df["preference_set_id"] = pid
        df["preference_set_name"] = pref_name
        df["run_id"] = run_id
        rows.append(df[["alternative_name", "score", "rank", "preference_set_name", "run_id"]])

        ddf = get_distances(run_id)
        if ddf is not None and not ddf.empty:
            ddf = ddf.copy()
            ddf["preference_set_name"] = pref_name
            ddf["run_id"] = run_id
            dist_rows.append(ddf)

        ideals_by_pref[pref_name] = get_ideals(run_id)
        weighted_by_pref[pref_name] = get_matrix(run_id, "weighted")
        normalized_by_pref[pref_name] = get_matrix(run_id, "normalized")

    if not rows:
        st.error("No results found for the selected sets. Run TOPSIS in Step 3 first.")
        st.session_state["cmp_ready"] = False
        st.session_state["cmp_payload"] = None
        st.stop()

    long_df = pd.concat(rows, ignore_index=True)

    if order_mode == "By rank of first preference set":
        base_pref = selected_prefs[0]
        base_name = pref_id_to_name.get(base_pref, base_pref)
        base_df = long_df[long_df["preference_set_name"] == base_name].copy()
        if not base_df.empty:
            base_df = base_df.sort_values("rank", ascending=True)
            alt_order = base_df["alternative_name"].tolist()
        else:
            alt_order = sorted(long_df["alternative_name"].unique().tolist())
    else:
        alt_order = sorted(long_df["alternative_name"].unique().tolist())

    long_df["alternative_name"] = pd.Categorical(long_df["alternative_name"], categories=alt_order, ordered=True)
    long_df = long_df.sort_values(["alternative_name", "preference_set_name"])

    dist_all = pd.concat(dist_rows, ignore_index=True) if dist_rows else pd.DataFrame()

    st.session_state["cmp_ready"] = True
    st.session_state["cmp_payload"] = {
        "long_df": long_df,
        "dist_all": dist_all,
        "ideals_by_pref": ideals_by_pref,
        "weighted_by_pref": weighted_by_pref,
        "normalized_by_pref": normalized_by_pref,
    }

payload = st.session_state.get("cmp_payload") if st.session_state.get("cmp_ready") else None

if isinstance(payload, dict) and payload:
    long_df = payload["long_df"]
    dist_all = payload["dist_all"]
    ideals_by_pref = payload["ideals_by_pref"]
    weighted_by_pref = payload["weighted_by_pref"]
    normalized_by_pref = payload["normalized_by_pref"]

    st.subheader("Scores by Alternative (Colored by Preference Set)")

    fig_scores = px.bar(
        long_df,
        x="alternative_name",
        y="score",
        color="preference_set_name",
        barmode="group",
        hover_data={
            "preference_set_name": True,
            "score": ":.6f",
            "rank": True,
            "run_id": True,
            "alternative_name": True,
        },
        labels={
            "alternative_name": "Alternative",
            "score": "TOPSIS Score (C*)",
            "preference_set_name": "Preference set",
        },
        title="TOPSIS Score comparison across preference sets",
    )
    st.plotly_chart(fig_scores, use_container_width=True)

    if st.session_state.get("cmp_show_rank_chart", True):
        st.subheader("Ranks by Alternative (Lower is better)")

        rank_df = long_df.copy()
        rank_df["rank_num"] = pd.to_numeric(rank_df["rank"], errors="coerce")

        fig_ranks = px.line(
            rank_df,
            x="alternative_name",
            y="rank_num",
            color="preference_set_name",
            markers=True,
            hover_data={
                "preference_set_name": True,
                "rank_num": True,
                "score": ":.6f",
                "run_id": True,
                "alternative_name": True,
            },
            labels={
                "alternative_name": "Alternative",
                "rank_num": "Rank (1 is best)",
                "preference_set_name": "Preference set",
            },
            title="Rank comparison across preference sets",
        )
        fig_ranks.update_yaxes(autorange="reversed")
        st.plotly_chart(fig_ranks, use_container_width=True)

    st.divider()
    st.subheader("Other Result Comparisons")

    show_distances = st.checkbox("Show Distances (S+, S-, C*)", value=True, key="cmp_show_dist")
    show_ideals = st.checkbox("Show Ideals valve view (PIS/NIS)", value=True, key="cmp_show_ideals")
    show_norm = st.checkbox("Show Normalized Matrix heatmaps", value=False, key="cmp_show_norm")
    show_weighted = st.checkbox("Show Weighted Matrix heatmaps", value=True, key="cmp_show_weighted")

    if show_distances:
        st.subheader("Distances comparison (S+, S-, C*)")

        if dist_all is None or dist_all.empty:
            st.info("No distances found for the selected runs.")
        else:
            fig_scatter = px.scatter(
                dist_all,
                x="s_pos",
                y="s_neg",
                color="preference_set_name",
                symbol="preference_set_name",
                hover_data={
                    "alternative": True,
                    "c_star": ":.6f",
                    "s_pos": ":.6f",
                    "s_neg": ":.6f",
                    "run_id": True,
                    "preference_set_name": True,
                },
                labels={
                    "s_pos": "S+ (distance to PIS)",
                    "s_neg": "S- (distance to NIS)",
                    "preference_set_name": "Preference set",
                },
                title="S+ vs S- across preference sets",
            )
            st.plotly_chart(fig_scatter, use_container_width=True)

            fig_cstar = px.bar(
                dist_all,
                x="alternative",
                y="c_star",
                color="preference_set_name",
                barmode="group",
                hover_data={"s_pos": ":.6f", "s_neg": ":.6f", "run_id": True},
                labels={
                    "alternative": "Alternative",
                    "c_star": "C* (closeness)",
                    "preference_set_name": "Preference set",
                },
                title="C* comparison across preference sets",
            )
            st.plotly_chart(fig_cstar, use_container_width=True)

    if show_ideals:
        st.subheader("Ideals valve view comparison (PIS/NIS)")

        criteria_union: list[str] = []
        for _, wdf in weighted_by_pref.items():
            if wdf is not None and not wdf.empty:
                criteria_union.extend(list(wdf.columns))
        criteria_union = sorted(list(dict.fromkeys(criteria_union)))

        if not criteria_union:
            st.info("No weighted matrices found for these runs.")
        else:
            picked_criterion = st.selectbox(
                "Criterion (valve view)",
                options=criteria_union,
                index=0,
                key="cmp_valve_criterion_pick",
            )

            fig_valve = go.Figure()
            xmin = None
            xmax = None

            for pref_name, wdf in weighted_by_pref.items():
                if wdf is None or wdf.empty:
                    continue
                if picked_criterion not in wdf.columns:
                    continue

                df_c = pd.DataFrame(
                    {"alternative": list(wdf.index), "weighted_value": wdf[picked_criterion].values}
                ).sort_values("weighted_value", ascending=False)

                if not df_c.empty:
                    xmn = float(df_c["weighted_value"].min())
                    xmx = float(df_c["weighted_value"].max())
                    xmin = xmn if xmin is None else min(xmin, xmn)
                    xmax = xmx if xmax is None else max(xmax, xmx)

                idf = ideals_by_pref.get(pref_name, pd.DataFrame())
                pos = None
                neg = None
                if idf is not None and not idf.empty and "criterion" in idf.columns:
                    row = idf[idf["criterion"] == picked_criterion]
                    if not row.empty:
                        pos = float(row.iloc[0]["pos_ideal"])
                        neg = float(row.iloc[0]["neg_ideal"])
                        xmin = pos if xmin is None else min(xmin, pos)
                        xmin = neg if xmin is None else min(xmin, neg)
                        xmax = pos if xmax is None else max(xmax, pos)
                        xmax = neg if xmax is None else max(xmax, neg)

                fig_valve.add_trace(
                    go.Scatter(
                        x=df_c["weighted_value"],
                        y=df_c["alternative"],
                        mode="markers",
                        name=pref_name,
                    )
                )

                if pos is not None:
                    fig_valve.add_vline(x=pos, line_width=2, line_dash="solid")
                if neg is not None:
                    fig_valve.add_vline(x=neg, line_width=2, line_dash="dash")

            if xmin is None or xmax is None:
                xmin, xmax = -1.0, 1.0
            pad = (xmax - xmin) * 0.08 if xmax > xmin else 0.1

            fig_valve.update_layout(
                title=f"Valve View: {picked_criterion} across sets",
                xaxis_title="Weighted value",
                yaxis_title="Alternative",
                height=520,
                margin=dict(l=10, r=10, t=70, b=10),
            )
            fig_valve.update_xaxes(range=[xmin - pad, xmax + pad])
            st.plotly_chart(fig_valve, use_container_width=True)

    if show_norm:
        st.subheader("Normalized matrix heatmaps (per preference set)")
        for pref_name, ndf in normalized_by_pref.items():
            if ndf is None or ndf.empty:
                st.caption(f"{pref_name}: no normalized matrix saved for this run.")
                continue
            st.markdown(f"**{pref_name}**")
            fig_n = px.imshow(
                ndf.values,
                x=list(ndf.columns),
                y=list(ndf.index),
                aspect="auto",
                title=f"Normalized Matrix Heatmap: {pref_name}",
            )
            st.plotly_chart(fig_n, use_container_width=True)

    if show_weighted:
        st.subheader("Weighted matrix heatmaps (per preference set)")
        present = [(name, df) for name, df in weighted_by_pref.items() if df is not None and not df.empty]

        for pref_name, wdf in present:
            st.markdown(f"**{pref_name}**")
            fig_w = px.imshow(
                wdf.values,
                x=list(wdf.columns),
                y=list(wdf.index),
                aspect="auto",
                title=f"Weighted Matrix Heatmap: {pref_name}",
            )
            st.plotly_chart(fig_w, use_container_width=True)

    st.download_button(
        "Download comparison data (CSV)",
        data=long_df.to_csv(index=False).encode("utf-8"),
        file_name="preference_set_comparison.csv",
        mime="text/csv",
    )
else:
    st.caption("Pick 2 to 5 preference sets and click Compare to generate charts.")
