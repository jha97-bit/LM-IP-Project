import bootstrap  # noqa: F401

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st
from app.ui_theme import apply_theme, BLUE_SCALE, TEAL_SCALE, BLUE_TEAL_SCALE, DISCRETE_PALETTE, section_header
from sqlalchemy import text

from app.app_context import guard_page, sync_method_from_scenario
from app.sidebar_nav import render_sidebar
from persistence.engine import get_engine
from persistence.repositories.preference_repo import PreferenceRepo
from persistence.repositories.result_repo import ResultRepo
from persistence.repositories.topsis_read_repo import TopsisReadRepo

st.set_page_config(page_title="MCDA - Sensitivity & Comparison", layout="wide")
apply_theme()
pio.templates.default = "plotly_white"
px.defaults.template = "plotly_white"

guard_page("pages/5_sensitivity.py")
sync_method_from_scenario()
render_sidebar("pages/5_sensitivity.py")

st.title("Step 5: Sensitivity Analysis & Preference Set Comparison")
section_header("Sensitivity Analysis & Preference Set Comparison", variant="gradient")

engine = get_engine()
pref_repo = PreferenceRepo(engine)
result_repo = ResultRepo(engine)
topsis_read_repo = TopsisReadRepo(engine)

scenario_id = st.session_state.get("scenario_id")
user_name = st.session_state.get("user_name", "")
method_choice = st.session_state.get("method_choice", "topsis")

if not scenario_id:
    st.warning("No scenario selected.")
    if st.button("← Go to Step 1"):
        st.switch_page("pages/1_decision_setup.py")
    st.stop()

nav_left, nav_right = st.columns(2)
with nav_left:
    if st.button("← Step 4: Results"):
        st.switch_page("pages/4_results.py")
with nav_right:
    if st.button("Next: Report Builder →", type="primary"):
        st.switch_page("pages/6_report_builder.py")

st.caption("Explore how weight changes affect rankings and compare results across preference sets.")
st.divider()

# -----------------------------------------------------------------------------
# Visual settings
# -----------------------------------------------------------------------------
CRITERION_PALETTE = [
    "#1F4E79",
    "#2A9D8F",
    "#5C7AEA",
    "#6C757D",
    "#00897B",
    "#7E57C2",
    "#577590",
    "#4361EE",
    "#264653",
    "#4A6FA5",
]

SET_PALETTE = [
    "#1F4E79",
    "#2A9D8F",
    "#5C7AEA",
    "#6C757D",
    "#00897B",
    "#7E57C2",
    "#264653",
    "#4A6FA5",
]

ALT_PALETTE = [
    "#1F4E79",
    "#2A9D8F",
    "#5C7AEA",
    "#6C757D",
    "#00897B",
    "#7E57C2",
    "#577590",
    "#4361EE",
    "#264653",
    "#4A6FA5",
    "#00A8A8",
    "#3A86FF",
]

MODEL_COLOR_MAP = {
    "Baseline": "#1F4E79",
    "Sandbox": "#2A9D8F",
}

DELTA_NEGATIVE_COLOR = "#5C7AEA"
DELTA_POSITIVE_COLOR = "#2A9D8F"
NEUTRAL_LINE = "#6C757D"

PATTERN_SEQUENCE = ["", "/", "\\", "x", ".", "+", "-"]


# -----------------------------------------------------------------------------
# Generic helpers
# -----------------------------------------------------------------------------
def color_map_from_labels(labels: list[str], palette: list[str]) -> dict[str, str]:
    uniq = []
    for item in labels:
        if item not in uniq:
            uniq.append(item)
    return {lab: palette[i % len(palette)] for i, lab in enumerate(uniq)}


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


def _rgb_to_hex(rgb: tuple[int, int, int]) -> str:
    return "#%02x%02x%02x" % rgb


def lighten_hex(hex_color: str, factor: float) -> str:
    factor = max(0.0, min(0.85, float(factor)))
    r, g, b = _hex_to_rgb(hex_color)
    new_rgb = (
        int(r + (255 - r) * factor),
        int(g + (255 - g) * factor),
        int(b + (255 - b) * factor),
    )
    return _rgb_to_hex(new_rgb)


def shade_levels(count: int) -> list[float]:
    if count <= 1:
        return [0.0]
    max_lighten = 0.55
    return [max_lighten * i / (count - 1) for i in range(count)]


def get_measurement_value_column() -> str:
    return "value_num"


def load_measurements_long(sid: str) -> list[dict]:
    value_col = get_measurement_value_column()
    sql = f"""
        SELECT
            a.name AS alternative_name,
            c.name AS criterion_name,
            m.{value_col} AS measurement_value
        FROM measurements m
        JOIN alternatives a ON a.alternative_id = m.alternative_id
        JOIN criteria c ON c.criterion_id = m.criterion_id
        WHERE m.scenario_id = :sid
        ORDER BY a.name, c.name
    """
    with engine.begin() as conn:
        rows = conn.execute(text(sql), {"sid": sid}).mappings().all()
    return [dict(r) for r in rows]


def load_prefs(sid: str) -> list[dict]:
    with engine.begin() as conn:
        rows = conn.execute(
            text(
                """
                SELECT preference_set_id::text, name
                FROM preference_sets
                WHERE scenario_id = :sid
                ORDER BY created_at DESC
                """
            ),
            {"sid": sid},
        ).mappings().all()
    return [dict(r) for r in rows]


def load_all_pref_options(method: str) -> list[dict]:
    with engine.begin() as conn:
        rows = conn.execute(
            text(
                """
                SELECT
                    p.preference_set_id::text AS preference_set_id,
                    p.name AS preference_name,
                    p.scenario_id::text AS scenario_id,
                    s.name AS scenario_name,
                    s.method_type,
                    d.title AS decision_title
                FROM preference_sets p
                JOIN scenarios s ON s.scenario_id = p.scenario_id
                JOIN decisions d ON d.decision_id = s.decision_id
                WHERE s.method_type = :method
                ORDER BY s.created_at DESC, p.created_at DESC
                """
            ),
            {"method": method},
        ).mappings().all()
    return [dict(r) for r in rows]


def load_runs_for_pref(sid: str, pid: str, method: str) -> list[dict]:
    with engine.begin() as conn:
        rows = conn.execute(
            text(
                """
                SELECT run_id::text, executed_at, executed_by, method
                FROM runs
                WHERE scenario_id = :sid
                  AND preference_set_id = :pid
                  AND method = :mth
                ORDER BY executed_at DESC
                LIMIT 100
                """
            ),
            {"sid": sid, "pid": pid, "mth": method},
        ).mappings().all()
    return [dict(r) for r in rows]


def get_scores(run_id: str) -> pd.DataFrame:
    return pd.DataFrame(result_repo.get_scores_with_names(run_id))


def get_distances(run_id: str) -> pd.DataFrame:
    df = topsis_read_repo.get_distances(run_id)
    return df if df is not None else pd.DataFrame()


def get_norm_matrix(run_id: str) -> pd.DataFrame:
    df = topsis_read_repo.get_matrix(run_id, "normalized")
    return df if df is not None else pd.DataFrame()


def get_weighted_matrix(run_id: str) -> pd.DataFrame:
    df = topsis_read_repo.get_matrix(run_id, "weighted")
    return df if df is not None else pd.DataFrame()


def get_vft_weighted_long(run_id: str) -> pd.DataFrame:
    with engine.begin() as conn:
        rows = conn.execute(
            text(
                """
                SELECT
                    a.name AS alternative_name,
                    c.name AS criterion_name,
                    vwu.weighted_utility AS weighted_value
                FROM vft_weighted_utilities vwu
                JOIN alternatives a ON a.alternative_id = vwu.alternative_id
                JOIN criteria c ON c.criterion_id = vwu.criterion_id
                WHERE vwu.run_id = :rid
                ORDER BY a.name, c.name
                """
            ),
            {"rid": run_id},
        ).mappings().all()

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    return df.rename(
        columns={
            "alternative_name": "Alternative",
            "criterion_name": "Criterion",
            "weighted_value": "Weighted Value",
        }
    )


def build_spider_chart(df_weighted: pd.DataFrame, selected_alts: list[str], title: str) -> go.Figure:
    fig = go.Figure()

    crit_labels = list(df_weighted.columns)
    if not crit_labels or not selected_alts:
        return fig

    crit_labels_closed = crit_labels + [crit_labels[0]]
    alt_color_map = color_map_from_labels(selected_alts, ALT_PALETTE)

    for alt in selected_alts:
        if alt not in df_weighted.index:
            continue
        vals = [float(df_weighted.loc[alt, c]) for c in crit_labels]
        vals_closed = vals + [vals[0]]
        fig.add_trace(
            go.Scatterpolar(
                r=vals_closed,
                theta=crit_labels_closed,
                fill="toself",
                name=alt,
                line=dict(color=alt_color_map[alt], width=2),
            )
        )

    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True)),
        title=title,
        height=500,
        margin=dict(l=20, r=20, t=60, b=20),
    )
    return fig


# -----------------------------------------------------------------------------
# TOPSIS helpers
# -----------------------------------------------------------------------------
def topsis_from_normalized(norm_df: pd.DataFrame, weights_by_name: dict, crit_meta_list: list[dict]) -> dict:
    if norm_df is None or norm_df.empty:
        return {}

    crits = list(norm_df.columns)
    w = np.array([float(weights_by_name.get(c, 0.0)) for c in crits], dtype=float)

    if w.sum() <= 0:
        w = np.ones(len(crits)) / len(crits)
    else:
        w = w / w.sum()

    w_series = pd.Series(w, index=crits)
    weighted_df = norm_df.astype(float).mul(w_series, axis=1)

    meta_by_name = {c["name"]: c for c in crit_meta_list}
    pos_ideal, neg_ideal = {}, {}

    for c in crits:
        direction = meta_by_name.get(c, {}).get("direction", "benefit")
        col = weighted_df[c].astype(float)
        if direction == "cost":
            pos_ideal[c] = float(col.min())
            neg_ideal[c] = float(col.max())
        else:
            pos_ideal[c] = float(col.max())
            neg_ideal[c] = float(col.min())

    pos_vec = np.array([pos_ideal[c] for c in crits])
    neg_vec = np.array([neg_ideal[c] for c in crits])
    x_mat = weighted_df[crits].astype(float).values

    s_pos = np.sqrt(((x_mat - pos_vec) ** 2).sum(axis=1))
    s_neg = np.sqrt(((x_mat - neg_vec) ** 2).sum(axis=1))

    denom = s_pos + s_neg
    denom[denom == 0] = 1e-12
    c_star = s_neg / denom

    ranking_df = (
        pd.DataFrame(
            {
                "alternative_name": list(norm_df.index),
                "score": c_star,
            }
        )
        .sort_values("score", ascending=False)
        .reset_index(drop=True)
    )
    ranking_df["rank"] = np.arange(1, len(ranking_df) + 1)

    dist_df = pd.DataFrame(
        {
            "alternative": list(norm_df.index),
            "s_pos": s_pos,
            "s_neg": s_neg,
            "c_star": c_star,
        }
    )

    return {
        "ranking_df": ranking_df,
        "dist_df": dist_df,
        "weighted_df": weighted_df,
        "weights_series": w_series,
    }


# -----------------------------------------------------------------------------
# VFT helpers
# -----------------------------------------------------------------------------
def load_vft_model_inputs(sid: str, preference_set_id: str) -> dict:
    weights_by_name = pref_repo.load_weights_by_criterion_name(preference_set_id)

    with engine.begin() as conn:
        crit_rows = conn.execute(
            text(
                """
                SELECT criterion_id::text AS criterion_id, name, direction
                FROM criteria
                WHERE scenario_id = :sid
                ORDER BY created_at, name
                """
            ),
            {"sid": sid},
        ).mappings().all()

        alt_rows = conn.execute(
            text(
                """
                SELECT alternative_id::text AS alternative_id, name
                FROM alternatives
                WHERE scenario_id = :sid
                ORDER BY created_at, name
                """
            ),
            {"sid": sid},
        ).mappings().all()

        vf_rows = conn.execute(
            text(
                """
                SELECT
                    c.name AS criterion_name,
                    vf.function_type,
                    vfp.point_order,
                    vfp.x,
                    vfp.y
                FROM value_functions vf
                JOIN criteria c ON c.criterion_id = vf.criterion_id
                LEFT JOIN value_function_points vfp ON vfp.value_function_id = vf.value_function_id
                WHERE vf.scenario_id = :sid
                ORDER BY c.name, vfp.point_order
                """
            ),
            {"sid": sid},
        ).mappings().all()

    meas_rows = load_measurements_long(sid)

    if not crit_rows or not alt_rows or not meas_rows:
        return {}

    alt_names = [r["name"] for r in alt_rows]
    crit_names = [r["name"] for r in crit_rows]

    raw_matrix = pd.DataFrame(index=alt_names, columns=crit_names, dtype=float)
    for r in meas_rows:
        raw_matrix.loc[r["alternative_name"], r["criterion_name"]] = float(r["measurement_value"])

    vf_map: dict[str, list[tuple[float, float]]] = {}
    for r in vf_rows:
        cname = r["criterion_name"]
        if cname not in vf_map:
            vf_map[cname] = []
        if r["x"] is not None and r["y"] is not None:
            vf_map[cname].append((float(r["x"]), float(r["y"])))

    attributes = []
    for r in crit_rows:
        cname = r["name"]
        direction = r.get("direction", "benefit")
        series = pd.to_numeric(raw_matrix[cname], errors="coerce").dropna()
        if series.empty:
            continue

        points = sorted(vf_map.get(cname, []), key=lambda x: x[0])

        if not points:
            min_val = float(series.min())
            max_val = float(series.max())
            if abs(max_val - min_val) < 1e-12:
                max_val = min_val + 1.0

            if direction == "cost":
                points = [(min_val, 1.0), (max_val, 0.0)]
                scaling_direction = "Decreasing"
            else:
                points = [(min_val, 0.0), (max_val, 1.0)]
                scaling_direction = "Increasing"
        else:
            scaling_direction = "Custom"

        attributes.append(
            {
                "name": cname,
                "weight": float(weights_by_name.get(cname, 0.0)),
                "points": points,
                "min_val": float(points[0][0]),
                "max_val": float(points[-1][0]),
                "unit": "",
                "scaling_direction": scaling_direction,
            }
        )

    return {
        "attributes": attributes,
        "alternatives": alt_names,
        "raw_matrix": raw_matrix,
    }


def interp_value_from_points(raw_value: float, points: list[tuple[float, float]]) -> float:
    if not points:
        return 0.0
    pts = sorted(points, key=lambda x: x[0])
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return float(np.interp(raw_value, xs, ys))


def compute_vft_base_scores(model_data: dict) -> tuple[dict, dict]:
    attributes = model_data["attributes"]
    alt_names = model_data["alternatives"]
    raw_matrix = model_data["raw_matrix"]

    alt_value_scores: dict[str, dict[str, float]] = {}
    base_total_scores: dict[str, float] = {}

    for alt in alt_names:
        alt_value_scores[alt] = {}
        total = 0.0
        for attr in attributes:
            raw = float(raw_matrix.loc[alt, attr["name"]])
            val = interp_value_from_points(raw, attr["points"])
            alt_value_scores[alt][attr["name"]] = val
            total += val * float(attr["weight"])
        base_total_scores[alt] = total

    return alt_value_scores, base_total_scores


# -----------------------------------------------------------------------------
# Cross scenario validation helpers
# -----------------------------------------------------------------------------
def get_scenario_signature(sid: str) -> dict:
    with engine.begin() as conn:
        alt_rows = conn.execute(
            text(
                """
                SELECT name
                FROM alternatives
                WHERE scenario_id = :sid
                ORDER BY name
                """
            ),
            {"sid": sid},
        ).mappings().all()

        crit_rows = conn.execute(
            text(
                """
                SELECT name, direction, scale_type
                FROM criteria
                WHERE scenario_id = :sid
                ORDER BY name
                """
            ),
            {"sid": sid},
        ).mappings().all()

    meas_rows = load_measurements_long(sid)

    alternatives = tuple(r["name"] for r in alt_rows)
    criteria = tuple((r["name"], r["direction"], r.get("scale_type")) for r in crit_rows)

    measurements = []
    for r in meas_rows:
        val = r["measurement_value"]
        if val is None:
            val_norm = None
        else:
            try:
                val_norm = round(float(val), 10)
            except Exception:
                val_norm = str(val)
        measurements.append((r["alternative_name"], r["criterion_name"], val_norm))

    return {
        "alternatives": alternatives,
        "criteria": criteria,
        "measurements": tuple(measurements),
    }


def validate_scenarios_comparable(
    scenario_ids: list[str],
    scenario_label_map: dict[str, str],
) -> tuple[bool, str]:
    uniq_sids = []
    for sid in scenario_ids:
        if sid not in uniq_sids:
            uniq_sids.append(sid)

    if len(uniq_sids) <= 1:
        return True, ""

    base_sid = uniq_sids[0]
    base_sig = get_scenario_signature(base_sid)

    for sid in uniq_sids[1:]:
        other_sig = get_scenario_signature(sid)

        if base_sig["alternatives"] != other_sig["alternatives"]:
            return (
                False,
                f"Alternatives differ between '{scenario_label_map.get(base_sid, base_sid)}' "
                f"and '{scenario_label_map.get(sid, sid)}'.",
            )

        if base_sig["criteria"] != other_sig["criteria"]:
            return (
                False,
                f"Criteria metadata differs between '{scenario_label_map.get(base_sid, base_sid)}' "
                f"and '{scenario_label_map.get(sid, sid)}'.",
            )

        if base_sig["measurements"] != other_sig["measurements"]:
            return (
                False,
                f"Input measurement data differs between '{scenario_label_map.get(base_sid, base_sid)}' "
                f"and '{scenario_label_map.get(sid, sid)}'. Cross-scenario comparison requires identical "
                f"alternatives, criteria, and measurements.",
            )

    return True, ""


# -----------------------------------------------------------------------------
# Comparison section helpers
# -----------------------------------------------------------------------------
def build_comparison_payload(selection_rows: list[dict], run_method: str) -> dict:
    rows = []
    dist_rows = []
    weighted_rows = []
    missing = []
    selection_order = []

    for sel in selection_rows:
        sid = sel["scenario_id"]
        pid = sel["preference_set_id"]
        comparison_label = sel["comparison_label"]

        runs_pref = load_runs_for_pref(sid, pid, run_method)
        if not runs_pref:
            missing.append(comparison_label)
            continue

        run_id = runs_pref[0]["run_id"]
        selection_order.append(comparison_label)

        sc_df = get_scores(run_id)
        if not sc_df.empty:
            sc_df = sc_df.copy()
            if "alternative" in sc_df.columns and "alternative_name" not in sc_df.columns:
                sc_df = sc_df.rename(columns={"alternative": "alternative_name"})
            sc_df["comparison_label"] = comparison_label
            sc_df["scenario_id"] = sid
            sc_df["preference_set_id"] = pid
            rows.append(
                sc_df[
                    ["alternative_name", "score", "rank", "comparison_label", "scenario_id", "preference_set_id"]
                ]
            )

        if run_method == "topsis":
            ddf = get_distances(run_id)
            if not ddf.empty:
                ddf = ddf.copy()
                ddf["comparison_label"] = comparison_label
                dist_rows.append(ddf)

            w_df = get_weighted_matrix(run_id)
            if w_df is not None and not w_df.empty:
                for alt in w_df.index:
                    for crit in w_df.columns:
                        weighted_rows.append(
                            {
                                "Alternative": alt,
                                "Criterion": crit,
                                "Weighted Value": float(w_df.loc[alt, crit]),
                                "comparison_label": comparison_label,
                            }
                        )

        elif run_method == "vft":
            vft_w_df = get_vft_weighted_long(run_id)
            if not vft_w_df.empty:
                vft_w_df = vft_w_df.copy()
                vft_w_df["comparison_label"] = comparison_label
                weighted_rows.extend(vft_w_df.to_dict(orient="records"))

    long_df = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()
    dist_df = pd.concat(dist_rows, ignore_index=True) if dist_rows else pd.DataFrame()
    weighted_long_df = pd.DataFrame(weighted_rows) if weighted_rows else pd.DataFrame()

    return {
        "long_df": long_df,
        "dist_df": dist_df,
        "weighted_long_df": weighted_long_df,
        "method": run_method,
        "missing": missing,
        "selection_order": selection_order,
    }


def render_grouped_stacked_score_chart(
    weighted_long_df: pd.DataFrame,
    selection_order: list[str],
    alt_order: list[str],
):
    section_header("Score and Criterion Contribution Comparison", variant="accent")
    st.caption(
        "Within each alternative, stacked bars appear in selected-set order. "
        "Bar height shows total score and stacked slices show criterion contribution. "
        "Preference sets are shown as lighter or darker shades of the same criterion color."
    )

    crit_order = list(pd.unique(weighted_long_df["Criterion"]))
    criterion_color_map = color_map_from_labels(crit_order, CRITERION_PALETTE)
    set_shades = {lab: shade_levels(len(selection_order))[i] for i, lab in enumerate(selection_order)}

    fig = go.Figure()

    for comp_label in selection_order:
        comp_df = weighted_long_df[weighted_long_df["comparison_label"] == comp_label]
        shade_factor = set_shades[comp_label]

        for crit in crit_order:
            trace_df = comp_df[comp_df["Criterion"] == crit]
            y_vals = []
            for alt in alt_order:
                row = trace_df[trace_df["Alternative"] == alt]
                y_vals.append(float(row["Weighted Value"].iloc[0]) if not row.empty else 0.0)

            fig.add_trace(
                go.Bar(
                    x=alt_order,
                    y=y_vals,
                    name=crit,
                    legendgroup=crit,
                    showlegend=(comp_label == selection_order[0]),
                    offsetgroup=comp_label,
                    marker=dict(
                        color=lighten_hex(criterion_color_map[crit], shade_factor),
                        line=dict(width=0),
                    ),
                    hovertemplate=(
                        "Alternative: %{x}<br>"
                        f"Set: {comp_label}<br>"
                        f"Criterion: {crit}<br>"
                        "Contribution: %{y:.4f}<extra></extra>"
                    ),
                )
            )

    fig.update_layout(
        barmode="stack",
        height=540,
        margin=dict(l=10, r=10, t=60, b=10),
        legend_title_text="Criterion",
        title="Alternative Score Composition Across Selected Sets",
    )
    st.plotly_chart(fig, use_container_width=True)

def render_rank_shift_chart(
    long_df: pd.DataFrame,
    selection_order: list[str],
    alt_order: list[str] | None = None,
):
    st.subheader("Rank Shift Across Selected Sets")
    st.caption(
        "Each line tracks how an alternative's rank moves across the selected sets. "
        "Steeper lines indicate stronger rank shifts."
    )

    rank_df = long_df.copy()
    rank_df["rank_num"] = pd.to_numeric(rank_df["rank"], errors="coerce")

    if alt_order is None:
        alt_order = (
            rank_df.groupby("alternative_name")["rank_num"]
            .mean()
            .sort_values()
            .index.tolist()
        )

    alt_color_map = color_map_from_labels(alt_order, ALT_PALETTE)

    fig = go.Figure()
    for alt in alt_order:
        adf = (
            rank_df[rank_df["alternative_name"] == alt][["comparison_label", "rank_num"]]
            .drop_duplicates()
            .set_index("comparison_label")
            .reindex(selection_order)
            .reset_index()
        )

        if adf["rank_num"].isna().all():
            continue

        fig.add_trace(
            go.Scatter(
                x=adf["comparison_label"],
                y=adf["rank_num"],
                mode="lines+markers",
                name=alt,
                line=dict(width=2.5, color=alt_color_map[alt]),
                marker=dict(size=9, color=alt_color_map[alt]),
                hovertemplate=(
                    "<b>%{fullData.name}</b><br>"
                    "Set: %{x}<br>"
                    "Rank: %{y}<extra></extra>"
                ),
            )
        )

    fig.update_yaxes(
        autorange="reversed",
        title="Rank (1 = Best)",
        tickmode="linear",
        tick0=1,
        dtick=1,
    )
    fig.update_xaxes(
        title="Selected Set",
        categoryorder="array",
        categoryarray=selection_order,
    )
    fig.update_layout(
        title="Rank Shift Chart",
        height=440,
        margin=dict(l=10, r=10, t=55, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
    )
    st.plotly_chart(fig, use_container_width=True)

    shift_summary = (
        rank_df.groupby("alternative_name")["rank_num"]
        .agg(lambda s: float(s.max() - s.min()) if len(s.dropna()) > 0 else 0.0)
        .sort_values(ascending=False)
    )
    if not shift_summary.empty:
        top_shift = shift_summary.index[0]
        st.info(
            f"Greatest observed rank movement: {top_shift} "
            f"(range of {shift_summary.iloc[0]:.0f} rank positions across the selected sets)."
        )


def render_distance_decomposition_chart(
    dist_df: pd.DataFrame,
    selection_order: list[str],
    alt_order: list[str],
):
    st.subheader("TOPSIS Distance Decomposition")
    st.caption(
        "Within each alternative, bars appear in selected-set order and show separate S+ and S- values."
    )

    set_color_map = color_map_from_labels(selection_order, SET_PALETTE)

    fig = go.Figure()

    for comp_label in selection_order:
        comp_df = dist_df[dist_df["comparison_label"] == comp_label]

        for distance_type, col_name in [("S+", "s_pos"), ("S-", "s_neg")]:
            y_vals = []
            c_vals = []
            for alt in alt_order:
                row = comp_df[comp_df["alternative"] == alt]
                if not row.empty:
                    y_vals.append(float(row[col_name].iloc[0]))
                    c_vals.append(float(row["c_star"].iloc[0]))
                else:
                    y_vals.append(0.0)
                    c_vals.append(np.nan)

            fig.add_trace(
                go.Bar(
                    x=alt_order,
                    y=y_vals,
                    name=f"{comp_label} | {distance_type}",
                    offsetgroup=f"{comp_label}_{distance_type}",
                    marker=dict(
                        color=lighten_hex(set_color_map[comp_label], 0.18 if distance_type == "S+" else 0.0),
                        line=dict(width=0),
                    ),
                    customdata=np.array(c_vals).reshape(-1, 1),
                    hovertemplate=(
                        "Alternative: %{x}<br>"
                        f"Set: {comp_label}<br>"
                        f"Distance: {distance_type}<br>"
                        "Value: %{y:.4f}<br>"
                        "C*: %{customdata[0]:.4f}<extra></extra>"
                    ),
                )
            )

    fig.update_layout(
        barmode="group",
        height=520,
        margin=dict(l=10, r=10, t=60, b=10),
        title="Distance Decomposition by Alternative Across Selected Sets",
    )
    st.plotly_chart(fig, use_container_width=True)


def render_comparison_section(payload: dict, csv_file_name: str):
    long_df = payload["long_df"]
    dist_df = payload["dist_df"]
    weighted_long_df = payload["weighted_long_df"]
    run_method = payload["method"]
    selection_order = payload["selection_order"]
    missing = payload["missing"]

    if missing:
        st.warning(f"No {run_method.upper()} runs found for: {', '.join(missing)}")

    if long_df.empty:
        st.info("No comparison results available for the selected sets.")
        return

    baseline_label = selection_order[0] if selection_order else long_df["comparison_label"].iloc[0]
    baseline_df = long_df[long_df["comparison_label"] == baseline_label].copy()

    if not baseline_df.empty:
        alt_order = baseline_df.sort_values("rank")["alternative_name"].tolist()
    else:
        alt_order = sorted(long_df["alternative_name"].dropna().unique().tolist())

    if not weighted_long_df.empty:
        render_grouped_stacked_score_chart(weighted_long_df, selection_order, alt_order)
    else:
        set_color_map = color_map_from_labels(selection_order, SET_PALETTE)
        fig_cmp = px.bar(
            long_df,
            x="alternative_name",
            y="score",
            color="comparison_label",
            barmode="group",
            category_orders={
                "alternative_name": alt_order,
                "comparison_label": selection_order,
            },
            color_discrete_map=set_color_map,
            title="Alternative Scores Across Selected Sets",
            labels={
                "alternative_name": "Alternative",
                "score": "Score",
                "comparison_label": "Selected Set",
            },
        )
        fig_cmp.update_layout(height=430, margin=dict(l=10, r=10, t=50, b=10))
        st.plotly_chart(fig_cmp, use_container_width=True)

    render_rank_shift_chart(long_df, selection_order, alt_order=alt_order)

    if run_method == "topsis" and not dist_df.empty:
        render_distance_decomposition_chart(dist_df, selection_order, alt_order)

    st.download_button(
        "⬇ Download Comparison CSV",
        data=long_df.to_csv(index=False).encode(),
        file_name=csv_file_name,
        mime="text/csv",
    )


# -----------------------------------------------------------------------------
# Sandbox helpers
# -----------------------------------------------------------------------------
def render_save_sandbox_weights(
    current_scenario_id: str,
    weights_sandbox: dict[str, float],
    current_user_name: str,
    key_suffix: str,
):
    st.markdown("**Save Sandbox Weights as New Preference Set**")
    sb_save_col1, sb_save_col2 = st.columns(2)

    with sb_save_col1:
        sb_name = st.text_input(
            "Preference set name",
            value="Sandbox Weights",
            key=f"sb_name_{key_suffix}",
        )

    with sb_save_col2:
        if st.button("💾 Save as Preference Set", type="secondary", key=f"sb_save_btn_{key_suffix}"):
            import uuid

            try:
                new_pid = str(uuid.uuid4())
                with engine.begin() as conn:
                    conn.execute(
                        text(
                            """
                            INSERT INTO preference_sets (
                                preference_set_id, scenario_id, type, name, status, created_by
                            )
                            VALUES (:pid, :sid, 'direct', :nm, 'active', :by)
                            """
                        ),
                        {
                            "pid": new_pid,
                            "sid": current_scenario_id,
                            "nm": sb_name.strip() or "Sandbox",
                            "by": current_user_name,
                        },
                    )

                    crit_rows_db = conn.execute(
                        text("SELECT criterion_id::text, name FROM criteria WHERE scenario_id = :sid"),
                        {"sid": current_scenario_id},
                    ).mappings().all()
                    crit_name_to_id = {r["name"]: r["criterion_id"] for r in crit_rows_db}

                    for cname, wval in weights_sandbox.items():
                        cid = crit_name_to_id.get(cname)
                        if cid:
                            conn.execute(
                                text(
                                    """
                                    INSERT INTO criterion_weights (preference_set_id, criterion_id, weight)
                                    VALUES (:pid, :cid, :w)
                                    ON CONFLICT (preference_set_id, criterion_id)
                                    DO UPDATE SET weight = EXCLUDED.weight
                                    """
                                ),
                                {"pid": new_pid, "cid": cid, "w": float(wval)},
                            )

                st.success(f"Saved preference set '{sb_name}'.")
            except Exception as e:
                st.error(f"Save failed: {e}")


def render_topsis_sandbox(
    current_scenario_id: str,
    baseline_run_id: str,
    picked_pref_sb: str,
    crit_meta_list: list[dict],
    weights_base: dict,
    weights_sandbox: dict,
    current_user_name: str,
):
    norm_df_base = get_norm_matrix(baseline_run_id)
    base_calc = topsis_from_normalized(norm_df_base, weights_base, crit_meta_list)
    sandbox_calc = topsis_from_normalized(norm_df_base, weights_sandbox, crit_meta_list)

    if not base_calc or norm_df_base.empty:
        st.info("TOPSIS sandbox could not be generated.")
        return

    col_rank, col_dist = st.columns(2)

    with col_rank:
        rb = base_calc["ranking_df"].rename(columns={"score": "score_base", "rank": "rank_base"})
        rs = sandbox_calc["ranking_df"].rename(columns={"score": "score_sandbox", "rank": "rank_sandbox"})
        merge = rb.merge(rs, on="alternative_name", how="outer")
        merge["score_delta"] = merge["score_sandbox"] - merge["score_base"]
        merge["bar_color"] = np.where(
            merge["score_delta"] >= 0,
            DELTA_POSITIVE_COLOR,
            DELTA_NEGATIVE_COLOR,
        )

        fig_delta = go.Figure(
            go.Bar(
                x=merge["alternative_name"],
                y=merge["score_delta"],
                marker_color=merge["bar_color"],
                hovertemplate="Alternative: %{x}<br>Score Δ: %{y:.4f}<extra></extra>",
            )
        )
        fig_delta.update_layout(
            title="Score Change (Sandbox - Baseline)",
            height=360,
            margin=dict(l=10, r=10, t=50, b=10),
            xaxis_title="Alternative",
            yaxis_title="Score Δ",
        )
        st.plotly_chart(fig_delta, use_container_width=True)

    with col_dist:
        dist_b = base_calc.get("dist_df")
        dist_s = sandbox_calc.get("dist_df")

        if dist_b is not None and not dist_b.empty and dist_s is not None and not dist_s.empty:
            dist_b = dist_b.copy()
            dist_b["model"] = "Baseline"

            dist_s = dist_s.copy()
            dist_s["model"] = "Sandbox"

            dist_compare = pd.concat([dist_b, dist_s], ignore_index=True)

            fig_dist_compare = px.scatter(
                dist_compare,
                x="s_pos",
                y="s_neg",
                color="model",
                symbol="alternative",
                text="alternative",
                color_discrete_map=MODEL_COLOR_MAP,
                title="Baseline vs Sandbox: S+ and S- Comparison",
                labels={"s_pos": "S+ (to PIS)", "s_neg": "S- (to NIS)"},
            )
            fig_dist_compare.update_traces(textposition="top center")
            fig_dist_compare.update_layout(height=360, margin=dict(l=10, r=10, t=50, b=10))

            for alt in dist_b["alternative"].unique():
                b_row = dist_b[dist_b["alternative"] == alt]
                s_row = dist_s[dist_s["alternative"] == alt]
                if not b_row.empty and not s_row.empty:
                    fig_dist_compare.add_trace(
                        go.Scatter(
                            x=[b_row["s_pos"].iloc[0], s_row["s_pos"].iloc[0]],
                            y=[b_row["s_neg"].iloc[0], s_row["s_neg"].iloc[0]],
                            mode="lines",
                            line=dict(dash="dot", width=1, color=NEUTRAL_LINE),
                            showlegend=False,
                            hoverinfo="skip",
                        )
                    )

            st.plotly_chart(fig_dist_compare, use_container_width=True)

    weighted_sb = sandbox_calc.get("weighted_df")
    if weighted_sb is not None and not weighted_sb.empty:
        st.subheader("Alternative Profile by Criteria (Spider Chart)")
        available_alts = list(weighted_sb.index)
        default_alts = available_alts[: min(3, len(available_alts))]
        selected_alts_spider = st.multiselect(
            "Select alternatives for spider chart",
            options=available_alts,
            default=default_alts,
            max_selections=5,
            key="sb_spider_alts_topsis",
        )
        if selected_alts_spider:
            fig_spider = build_spider_chart(
                weighted_sb,
                selected_alts_spider,
                "Spider Chart: Weighted Criterion Profile (Sandbox)",
            )
            st.plotly_chart(fig_spider, use_container_width=True)

    base_alt_order = rb.sort_values("rank_base")["alternative_name"].tolist() if not rb.empty else list(norm_df_base.index)
    render_topsis_sandbox_advanced(
        norm_df_base=norm_df_base,
        crit_meta_list=crit_meta_list,
        weights_base=weights_base,
        alt_order_default=base_alt_order,
    )

    render_save_sandbox_weights(
        current_scenario_id=current_scenario_id,
        weights_sandbox=weights_sandbox,
        current_user_name=current_user_name,
        key_suffix="topsis",
    )


def render_topsis_sandbox_advanced(
    norm_df_base: pd.DataFrame,
    crit_meta_list: list[dict],
    weights_base: dict,
    alt_order_default: list[str] | None = None,
):
    if norm_df_base is None or norm_df_base.empty:
        return

    section_header("Additional Sandbox Views", variant="accent")
    st.caption("These views extend the sandbox without creating a separate TOPSIS section.")

    crits = list(norm_df_base.columns)
    alt_names = list(norm_df_base.index)
    if not crits or not alt_names:
        return

    alt_order_default = alt_order_default or alt_names
    alt_color_map = color_map_from_labels(alt_names, ALT_PALETTE)

    weight_attr = st.selectbox(
        "Criterion to vary",
        crits,
        key="topsis_weight_sens_attr",
    )

    weight_range = np.linspace(0.0, 1.0, 50)
    other_crits = [c for c in crits if c != weight_attr]
    base_other_weights = {c: float(weights_base.get(c, 0.0)) for c in other_crits}
    sum_other_weights = sum(base_other_weights.values())

    plot_rows = []
    for w in weight_range:
        temp_weights = {c: 0.0 for c in crits}
        temp_weights[weight_attr] = float(w)
        remaining_weight = 1.0 - float(w)

        if other_crits:
            if sum_other_weights > 0:
                for oc in other_crits:
                    temp_weights[oc] = remaining_weight * base_other_weights[oc] / sum_other_weights
            else:
                equal_weight = remaining_weight / len(other_crits)
                for oc in other_crits:
                    temp_weights[oc] = equal_weight

        temp_calc = topsis_from_normalized(norm_df_base, temp_weights, crit_meta_list)
        rdf = temp_calc.get("ranking_df", pd.DataFrame())
        for _, row in rdf.iterrows():
            plot_rows.append(
                {
                    "Weight of Selected Criterion": w,
                    "Alternative": row["alternative_name"],
                    "Score": row["score"],
                }
            )

    if plot_rows:
        df_w = pd.DataFrame(plot_rows)
        fig_w = px.line(
            df_w,
            x="Weight of Selected Criterion",
            y="Score",
            color="Alternative",
            color_discrete_map=alt_color_map,
            title=f"Weight Sensitivity for {weight_attr}",
            labels={
                "Weight of Selected Criterion": f"Weight of {weight_attr}",
                "Score": "TOPSIS Score",
            },
        )
        fig_w.add_vline(
            x=float(weights_base.get(weight_attr, 0.0)),
            line_dash="dash",
            line_color=NEUTRAL_LINE,
            annotation_text="Current Weight",
            annotation_position="top right",
        )
        fig_w.update_layout(yaxis_range=[-0.02, 1.02], xaxis_range=[-0.02, 1.02], height=440)
        st.plotly_chart(fig_w, use_container_width=True)

    selected_alt_name_r = st.selectbox(
        "Alternative for robustness chart",
        alt_names,
        index=0 if not alt_order_default else alt_names.index(alt_order_default[0]) if alt_order_default[0] in alt_names else 0,
        key="topsis_robust_sens_alt",
    )

    base_calc = topsis_from_normalized(norm_df_base, weights_base, crit_meta_list)
    base_score_df = base_calc.get("ranking_df", pd.DataFrame())
    base_score_map = dict(zip(base_score_df.get("alternative_name", []), base_score_df.get("score", [])))
    base_score = float(base_score_map.get(selected_alt_name_r, 0.0))

    tornado_data = []
    for crit in crits:
        other_crits = [c for c in crits if c != crit]
        base_other_weights = {c: float(weights_base.get(c, 0.0)) for c in other_crits}
        sum_other_weights = sum(base_other_weights.values())

        w0 = {c: 0.0 for c in crits}
        w1 = {c: 0.0 for c in crits}
        w1[crit] = 1.0

        if other_crits:
            if sum_other_weights > 0:
                for oc in other_crits:
                    w0[oc] = base_other_weights[oc] / sum_other_weights
            else:
                eq = 1.0 / len(other_crits)
                for oc in other_crits:
                    w0[oc] = eq

        calc_w0 = topsis_from_normalized(norm_df_base, w0, crit_meta_list)
        calc_w1 = topsis_from_normalized(norm_df_base, w1, crit_meta_list)
        score_map_w0 = dict(zip(calc_w0["ranking_df"]["alternative_name"], calc_w0["ranking_df"]["score"]))
        score_map_w1 = dict(zip(calc_w1["ranking_df"]["alternative_name"], calc_w1["ranking_df"]["score"]))
        w0_score = float(score_map_w0.get(selected_alt_name_r, 0.0))
        w1_score = float(score_map_w1.get(selected_alt_name_r, 0.0))

        min_score = min(w0_score, w1_score)
        max_score = max(w0_score, w1_score)
        tornado_data.append(
            {
                "Criterion": crit,
                "Base Score": base_score,
                "Weight0 Score": w0_score,
                "Weight1 Score": w1_score,
                "Min Score": min_score,
                "Max Score": max_score,
                "Spread": max_score - min_score,
            }
        )

    df_t = pd.DataFrame(tornado_data)
    if not df_t.empty:
        df_t = df_t.sort_values(by="Spread", ascending=True).reset_index(drop=True)
        fig_t = go.Figure()
        fig_t.add_shape(
            type="line",
            x0=base_score,
            y0=-0.5,
            x1=base_score,
            y1=len(df_t) - 0.5,
            line=dict(color=NEUTRAL_LINE, width=2, dash="dash"),
        )
        fig_t.add_trace(
            go.Bar(
                y=df_t["Criterion"],
                x=df_t["Max Score"] - df_t["Min Score"],
                base=df_t["Min Score"],
                orientation="h",
                marker_color="#A8DADC",
                hovertemplate=(
                    "Criterion: %{y}<br>"
                    "Range Start: %{base:.4f}<br>"
                    "Range Width: %{x:.4f}<extra></extra>"
                ),
                showlegend=False,
            )
        )
        fig_t.add_trace(
            go.Scatter(
                x=df_t["Weight0 Score"],
                y=df_t["Criterion"],
                mode="markers",
                marker=dict(size=10, color="#1F4E79"),
                name="Weight = 0",
            )
        )
        fig_t.add_trace(
            go.Scatter(
                x=df_t["Weight1 Score"],
                y=df_t["Criterion"],
                mode="markers",
                marker=dict(size=10, color="#2A9D8F"),
                name="Weight = 1",
            )
        )
        fig_t.update_layout(
            title=f"Robustness Tornado Chart for {selected_alt_name_r}",
            xaxis_title="TOPSIS Score",
            yaxis_title="Criterion",
            xaxis_range=[0, 1.05],
            height=460,
            margin=dict(l=10, r=10, t=55, b=10),
        )
        st.plotly_chart(fig_t, use_container_width=True)


def render_vft_sandbox(
    current_scenario_id: str,
    picked_pref_sb: str,
    weights_base: dict,
    weights_sandbox: dict,
    current_user_name: str,
):
    model_data = load_vft_model_inputs(current_scenario_id, picked_pref_sb)
    if not model_data:
        st.info("VFT sandbox could not be generated.")
        return

    attributes = model_data["attributes"]
    alt_names = model_data["alternatives"]
    raw_matrix = model_data["raw_matrix"]

    base_attr_map = {a["name"]: dict(a) for a in attributes}
    for a in base_attr_map.values():
        a["weight"] = float(weights_base.get(a["name"], 0.0))
    base_model_data = {
        "attributes": list(base_attr_map.values()),
        "alternatives": alt_names,
        "raw_matrix": raw_matrix,
    }

    sandbox_attr_map = {a["name"]: dict(a) for a in attributes}
    for a in sandbox_attr_map.values():
        a["weight"] = float(weights_sandbox.get(a["name"], 0.0))
    sandbox_model_data = {
        "attributes": list(sandbox_attr_map.values()),
        "alternatives": alt_names,
        "raw_matrix": raw_matrix,
    }

    base_value_scores, base_total_scores = compute_vft_base_scores(base_model_data)
    sandbox_value_scores, sandbox_total_scores = compute_vft_base_scores(sandbox_model_data)

    base_df = pd.DataFrame(
        [{"alternative_name": k, "score_base": v} for k, v in base_total_scores.items()]
    ).sort_values("score_base", ascending=False).reset_index(drop=True)
    base_df["rank_base"] = np.arange(1, len(base_df) + 1)

    sandbox_df = pd.DataFrame(
        [{"alternative_name": k, "score_sandbox": v} for k, v in sandbox_total_scores.items()]
    ).sort_values("score_sandbox", ascending=False).reset_index(drop=True)
    sandbox_df["rank_sandbox"] = np.arange(1, len(sandbox_df) + 1)

    merge = base_df.merge(sandbox_df, on="alternative_name", how="outer")
    merge["score_delta"] = merge["score_sandbox"] - merge["score_base"]
    merge["bar_color"] = np.where(
        merge["score_delta"] >= 0,
        DELTA_POSITIVE_COLOR,
        DELTA_NEGATIVE_COLOR,
    )

    col_rank, col_compare = st.columns(2)

    with col_rank:
        fig_delta = go.Figure(
            go.Bar(
                x=merge["alternative_name"],
                y=merge["score_delta"],
                marker_color=merge["bar_color"],
                hovertemplate="Alternative: %{x}<br>Score Δ: %{y:.4f}<extra></extra>",
            )
        )
        fig_delta.update_layout(
            title="VFT Score Change (Sandbox - Baseline)",
            height=360,
            margin=dict(l=10, r=10, t=50, b=10),
            xaxis_title="Alternative",
            yaxis_title="Score Δ",
        )
        st.plotly_chart(fig_delta, use_container_width=True)

    with col_compare:
        compare_df = pd.concat(
            [
                pd.DataFrame(
                    {
                        "alternative_name": list(base_total_scores.keys()),
                        "score": list(base_total_scores.values()),
                        "model": "Baseline",
                    }
                ),
                pd.DataFrame(
                    {
                        "alternative_name": list(sandbox_total_scores.keys()),
                        "score": list(sandbox_total_scores.values()),
                        "model": "Sandbox",
                    }
                ),
            ],
            ignore_index=True,
        )

        fig_compare = px.bar(
            compare_df,
            x="alternative_name",
            y="score",
            color="model",
            barmode="group",
            color_discrete_map=MODEL_COLOR_MAP,
            title="Baseline vs Sandbox Total Scores",
            labels={"alternative_name": "Alternative", "score": "Score"},
        )
        fig_compare.update_layout(height=360, margin=dict(l=10, r=10, t=50, b=10))
        st.plotly_chart(fig_compare, use_container_width=True)

    st.subheader("VFT Rank Shift")
    rank_shift_df = pd.concat(
        [
            pd.DataFrame(
                {
                    "alternative_name": merge["alternative_name"],
                    "comparison_label": "Baseline",
                    "rank": base_df.set_index("alternative_name").reindex(merge["alternative_name"])["rank_base"].values,
                }
            ),
            pd.DataFrame(
                {
                    "alternative_name": merge["alternative_name"],
                    "comparison_label": "Sandbox",
                    "rank": sandbox_df.set_index("alternative_name").reindex(merge["alternative_name"])["rank_sandbox"].values,
                }
            ),
        ],
        ignore_index=True,
    )
    render_rank_shift_chart(rank_shift_df, ["Baseline", "Sandbox"])

    weighted_rows = []
    crit_names = [a["name"] for a in sandbox_model_data["attributes"]]
    for alt in alt_names:
        for crit in crit_names:
            weighted_rows.append(
                {
                    "Alternative": alt,
                    "Criterion": crit,
                    "Weighted Value": sandbox_value_scores[alt][crit] * weights_sandbox.get(crit, 0.0),
                }
            )

    weighted_sb = pd.DataFrame(weighted_rows).pivot(
        index="Alternative",
        columns="Criterion",
        values="Weighted Value",
    )

    if not weighted_sb.empty:
        st.subheader("Alternative Profile by Criteria (Spider Chart)")
        available_alts = list(weighted_sb.index)
        default_alts = available_alts[: min(3, len(available_alts))]
        selected_alts_spider = st.multiselect(
            "Select alternatives for spider chart",
            options=available_alts,
            default=default_alts,
            max_selections=5,
            key="sb_spider_alts_vft",
        )
        if selected_alts_spider:
            fig_spider = build_spider_chart(
                weighted_sb,
                selected_alts_spider,
                "Spider Chart: Weighted Criterion Profile (Sandbox)",
            )
            st.plotly_chart(fig_spider, use_container_width=True)

    render_vft_sandbox_advanced_inline(
        attributes=attributes,
        alt_names=alt_names,
        raw_matrix=raw_matrix,
        alt_value_scores=base_value_scores,
        base_total_scores=base_total_scores,
    )

    render_save_sandbox_weights(
        current_scenario_id=current_scenario_id,
        weights_sandbox=weights_sandbox,
        current_user_name=current_user_name,
        key_suffix="vft",
    )


def render_vft_sandbox_advanced_inline(
    attributes: list[dict],
    alt_names: list[str],
    raw_matrix: pd.DataFrame,
    alt_value_scores: dict,
    base_total_scores: dict,
):
    if not attributes or not alt_names:
        return

    section_header("Additional Sandbox Views", variant="accent")
    st.caption("These views extend the sandbox without creating a separate VFT section.")

    ranked_alts = sorted(base_total_scores.items(), key=lambda item: item[1], reverse=True)
    alt_color_map = color_map_from_labels(alt_names, ALT_PALETTE)

    st.markdown("**Weight Sensitivity**")
    attr_names = [a["name"] for a in attributes]
    selected_attr_name_w = st.selectbox(
        "Objective to vary",
        attr_names,
        key="vft_weight_sens_attr_inline",
    )
    selected_attr_w = next((a for a in attributes if a["name"] == selected_attr_name_w), None)

    if selected_attr_w:
        weight_range = np.linspace(0.0, 1.0, 50)
        other_attrs = [a for a in attributes if a["name"] != selected_attr_w["name"]]
        base_other_weights = {a["name"]: float(a["weight"]) for a in other_attrs}
        sum_other_weights = sum(base_other_weights.values())

        plot_data_w = []
        for w in weight_range:
            for alt in alt_names:
                total_score = alt_value_scores[alt][selected_attr_w["name"]] * w

                if sum_other_weights > 0:
                    remaining_weight = 1.0 - w
                    for other_attr in other_attrs:
                        proportional_weight = base_other_weights[other_attr["name"]] / sum_other_weights * remaining_weight
                        total_score += alt_value_scores[alt][other_attr["name"]] * proportional_weight
                elif other_attrs:
                    remaining_weight = 1.0 - w
                    equal_weight = remaining_weight / len(other_attrs)
                    for other_attr in other_attrs:
                        total_score += alt_value_scores[alt][other_attr["name"]] * equal_weight

                plot_data_w.append(
                    {
                        "Weight of Selected Objective": w,
                        "Alternative": alt,
                        "Total Score": total_score,
                    }
                )

        df_w = pd.DataFrame(plot_data_w)
        fig_w = px.line(
            df_w,
            x="Weight of Selected Objective",
            y="Total Score",
            color="Alternative",
            color_discrete_map=alt_color_map,
            title=f"Weight Sensitivity for {selected_attr_w['name']}",
            labels={
                "Weight of Selected Objective": f"Weight of {selected_attr_w['name']}",
                "Total Score": "Overall Score",
            },
        )
        fig_w.add_vline(
            x=float(selected_attr_w["weight"]),
            line_dash="dash",
            line_color=NEUTRAL_LINE,
            annotation_text="Current Weight",
            annotation_position="top right",
        )
        fig_w.update_layout(yaxis_range=[-0.02, 1.05], xaxis_range=[-0.02, 1.02], height=440)
        st.plotly_chart(fig_w, use_container_width=True)

    st.markdown("**Objective Score Sensitivity**")
    col1, col2 = st.columns(2)
    with col1:
        selected_alt_name_s = st.selectbox(
            "Alternative",
            alt_names,
            key="vft_score_sens_alt_inline",
        )
    with col2:
        selected_attr_name_s = st.selectbox(
            "Objective to vary",
            [a["name"] for a in attributes],
            key="vft_score_sens_attr_inline",
        )

    selected_attr_s = next((a for a in attributes if a["name"] == selected_attr_name_s), None)
    if selected_attr_s:
        score_range = np.linspace(float(selected_attr_s["min_val"]), float(selected_attr_s["max_val"]), 50)
        other_alts = [a for a in alt_names if a != selected_alt_name_s]
        plot_data_s = []
        for score in score_range:
            new_val = interp_value_from_points(score, selected_attr_s["points"])
            new_total = 0.0
            for attr in attributes:
                if attr["name"] == selected_attr_s["name"]:
                    new_total += new_val * float(attr["weight"])
                else:
                    new_total += alt_value_scores[selected_alt_name_s][attr["name"]] * float(attr["weight"])
            plot_data_s.append({"Raw Score": score, "Alternative": selected_alt_name_s, "Total Score": new_total})
            for other_alt in other_alts:
                plot_data_s.append({"Raw Score": score, "Alternative": other_alt, "Total Score": base_total_scores[other_alt]})

        df_s = pd.DataFrame(plot_data_s)
        fig_s = px.line(
            df_s,
            x="Raw Score",
            y="Total Score",
            color="Alternative",
            color_discrete_map=alt_color_map,
            title=f"Score Sensitivity for {selected_alt_name_s} on {selected_attr_s['name']}",
            labels={"Raw Score": "Raw Score", "Total Score": "Overall Score"},
        )
        current_raw_score = float(raw_matrix.loc[selected_alt_name_s, selected_attr_s["name"]])
        fig_s.add_vline(
            x=current_raw_score,
            line_dash="dash",
            line_color=NEUTRAL_LINE,
            annotation_text="Current Score",
            annotation_position="top right",
        )
        fig_s.update_layout(yaxis_range=[-0.02, 1.05], height=440)
        st.plotly_chart(fig_s, use_container_width=True)

    st.markdown("**Robustness Analysis**")
    top_alt_name = ranked_alts[0][0] if ranked_alts else alt_names[0]
    selected_alt_name_r = st.selectbox(
        "Alternative for robustness chart",
        alt_names,
        index=alt_names.index(top_alt_name) if top_alt_name in alt_names else 0,
        key="vft_robust_sens_alt_inline",
    )

    tornado_data = []
    base_score = base_total_scores[selected_alt_name_r]
    for attr in attributes:
        other_attrs = [a for a in attributes if a["name"] != attr["name"]]
        base_other_weights = {a["name"]: float(a["weight"]) for a in other_attrs}
        sum_other_weights = sum(base_other_weights.values())

        w0_score = 0.0
        if sum_other_weights > 0:
            for other_attr in other_attrs:
                proportional_weight = base_other_weights[other_attr["name"]] / sum_other_weights
                w0_score += alt_value_scores[selected_alt_name_r][other_attr["name"]] * proportional_weight
        elif other_attrs:
            equal_weight = 1.0 / len(other_attrs)
            for other_attr in other_attrs:
                w0_score += alt_value_scores[selected_alt_name_r][other_attr["name"]] * equal_weight

        w1_score = alt_value_scores[selected_alt_name_r][attr["name"]] * 1.0
        min_score = min(w0_score, w1_score)
        max_score = max(w0_score, w1_score)
        tornado_data.append(
            {
                "Objective": attr["name"],
                "Base Score": base_score,
                "Weight0 Score": w0_score,
                "Weight1 Score": w1_score,
                "Min Score": min_score,
                "Max Score": max_score,
                "Spread": max_score - min_score,
            }
        )

    df_t = pd.DataFrame(tornado_data)
    if not df_t.empty:
        df_t = df_t.sort_values(by="Spread", ascending=True).reset_index(drop=True)
        fig_t = go.Figure()
        fig_t.add_shape(
            type="line",
            x0=base_score,
            y0=-0.5,
            x1=base_score,
            y1=len(df_t) - 0.5,
            line=dict(color=NEUTRAL_LINE, width=2, dash="dash"),
        )
        fig_t.add_trace(
            go.Bar(
                y=df_t["Objective"],
                x=df_t["Max Score"] - df_t["Min Score"],
                base=df_t["Min Score"],
                orientation="h",
                marker_color="#A8DADC",
                hovertemplate="Objective: %{y}<br>Range Start: %{base:.4f}<br>Range Width: %{x:.4f}<extra></extra>",
                showlegend=False,
            )
        )
        fig_t.add_trace(go.Scatter(x=df_t["Weight0 Score"], y=df_t["Objective"], mode="markers", marker=dict(size=10, color="#1F4E79"), name="Weight = 0"))
        fig_t.add_trace(go.Scatter(x=df_t["Weight1 Score"], y=df_t["Objective"], mode="markers", marker=dict(size=10, color="#2A9D8F"), name="Weight = 1"))
        fig_t.update_layout(
            title=f"Robustness Tornado Chart for {selected_alt_name_r}",
            xaxis_title="Overall Score",
            yaxis_title="Objective",
            xaxis_range=[0, 1.05],
            height=460,
            margin=dict(l=10, r=10, t=55, b=10),
        )
        st.plotly_chart(fig_t, use_container_width=True)


def render_common_sandbox_section(
    current_scenario_id: str,
    prefs_for_scenario: list[dict],
    pref_name_map: dict[str, str],
    current_method_choice: str,
    current_user_name: str,
):
    st.header("🔬 Sensitivity Analysis - Weight Sandbox")
    st.caption("Adjust weights interactively to see how ranking changes without saving a new run.")

    if not prefs_for_scenario:
        st.info("No preference sets found.")
        return

    pref_ids_local = [p["preference_set_id"] for p in prefs_for_scenario]
    default_pref = st.session_state.get("preference_set_id") or pref_ids_local[0]
    if default_pref not in pref_ids_local:
        default_pref = pref_ids_local[0]

    picked_sb_pref = st.multiselect(
        "Baseline preference set",
        options=pref_ids_local,
        default=[default_pref],
        max_selections=1,
        format_func=lambda x: pref_name_map.get(x, x),
        key=f"sb_baseline_pref_{current_method_choice}",
    )
    picked_pref_sb = picked_sb_pref[0] if picked_sb_pref else pref_ids_local[0]

    runs_sb = load_runs_for_pref(current_scenario_id, picked_pref_sb, current_method_choice)
    if not runs_sb:
        st.info(f"No {current_method_choice.upper()} runs found for this preference set. Run the model first.")
        return

    with engine.begin() as conn:
        crit_meta = conn.execute(
            text(
                """
                SELECT name, direction, scale_type
                FROM criteria
                WHERE scenario_id = :sid
                ORDER BY created_at
                """
            ),
            {"sid": current_scenario_id},
        ).mappings().all()
    crit_meta_list = [dict(r) for r in crit_meta]

    crits = [c["name"] for c in crit_meta_list]
    weights_base = pref_repo.load_weights_by_criterion_name(picked_pref_sb)

    base_w_vec = np.array([float(weights_base.get(c, 0.0)) for c in crits], dtype=float)
    if base_w_vec.sum() > 0:
        base_w_vec = base_w_vec / base_w_vec.sum()
    else:
        base_w_vec = np.ones(len(crits)) / max(1, len(crits))

    st.markdown("**Adjust Weights**")
    wt_cols = st.columns(min(5, max(1, len(crits))))
    sandbox_weights_raw = {}

    for i, c in enumerate(crits):
        with wt_cols[i % len(wt_cols)]:
            sandbox_weights_raw[c] = st.slider(
                c,
                0.0,
                1.0,
                float(base_w_vec[i]),
                step=0.01,
                key=f"sb_slider_{current_method_choice}_{picked_pref_sb}_{c}",
            )

    auto_norm = st.checkbox(
        "Auto-normalize sandbox weights",
        value=True,
        key=f"sb_autonorm_{current_method_choice}",
    )

    w_sb = np.array([float(sandbox_weights_raw[c]) for c in crits], dtype=float)
    if auto_norm and w_sb.sum() > 0:
        w_sb = w_sb / w_sb.sum()

    weights_sandbox = {crits[i]: float(w_sb[i]) for i in range(len(crits))}

    if current_method_choice == "topsis":
        baseline_run_id = runs_sb[0]["run_id"]
        render_topsis_sandbox(
            current_scenario_id=current_scenario_id,
            baseline_run_id=baseline_run_id,
            picked_pref_sb=picked_pref_sb,
            crit_meta_list=crit_meta_list,
            weights_base=weights_base,
            weights_sandbox=weights_sandbox,
            current_user_name=current_user_name,
        )
    else:
        render_vft_sandbox(
            current_scenario_id=current_scenario_id,
            picked_pref_sb=picked_pref_sb,
            weights_base=weights_base,
            weights_sandbox=weights_sandbox,
            current_user_name=current_user_name,
        )


# -----------------------------------------------------------------------------
# VFT extra insights, inline on same page
# -----------------------------------------------------------------------------
def render_vft_advanced_sensitivity(
    current_scenario_id: str,
    prefs_for_scenario: list[dict],
    pref_name_map: dict[str, str],
):
    st.divider()
    st.header("VFT Advanced Sensitivity")
    st.caption("Additional VFT-only views appear below the sandbox on the same page.")

    if not prefs_for_scenario:
        st.info("No preference sets are available for this VFT scenario.")
        return

    pref_ids_local = [p["preference_set_id"] for p in prefs_for_scenario]
    default_pref_local = st.session_state.get("preference_set_id") or pref_ids_local[0]
    if default_pref_local not in pref_ids_local:
        default_pref_local = pref_ids_local[0]

    selected_vft_pref = st.selectbox(
        "Preference set for VFT advanced sensitivity",
        options=pref_ids_local,
        index=pref_ids_local.index(default_pref_local),
        format_func=lambda x: pref_name_map.get(x, x),
        key="vft_sens_pref",
    )

    model_data = load_vft_model_inputs(current_scenario_id, selected_vft_pref)
    if not model_data:
        st.info("VFT sensitivity views need criteria, alternatives, measurements, and value-function data.")
        return

    attributes = model_data["attributes"]
    alt_names = model_data["alternatives"]
    raw_matrix = model_data["raw_matrix"]

    if not attributes or not alt_names:
        st.info("VFT sensitivity views need valid attributes and alternatives.")
        return

    alt_value_scores, base_total_scores = compute_vft_base_scores(model_data)
    ranked_alts = sorted(base_total_scores.items(), key=lambda item: item[1], reverse=True)
    alt_color_map = color_map_from_labels(alt_names, ALT_PALETTE)

    # 1. Weight sensitivity
    st.subheader("Weight Sensitivity")
    st.caption("See how changing the weight of one objective affects total scores for all alternatives.")

    attr_names = [a["name"] for a in attributes]
    selected_attr_name_w = st.selectbox(
        "Select objective to vary",
        attr_names,
        key="vft_weight_sens_attr",
    )
    selected_attr_w = next((a for a in attributes if a["name"] == selected_attr_name_w), None)

    if selected_attr_w:
        weight_range = np.linspace(0.0, 1.0, 50)
        other_attrs = [a for a in attributes if a["name"] != selected_attr_w["name"]]
        base_other_weights = {a["name"]: float(a["weight"]) for a in other_attrs}
        sum_other_weights = sum(base_other_weights.values())

        plot_data_w = []
        for w in weight_range:
            for alt in alt_names:
                total_score = alt_value_scores[alt][selected_attr_w["name"]] * w

                if sum_other_weights > 0:
                    remaining_weight = 1.0 - w
                    for other_attr in other_attrs:
                        proportional_weight = (
                            base_other_weights[other_attr["name"]] / sum_other_weights * remaining_weight
                        )
                        total_score += alt_value_scores[alt][other_attr["name"]] * proportional_weight
                else:
                    if other_attrs:
                        remaining_weight = 1.0 - w
                        equal_weight = remaining_weight / len(other_attrs)
                        for other_attr in other_attrs:
                            total_score += alt_value_scores[alt][other_attr["name"]] * equal_weight

                plot_data_w.append(
                    {
                        "Weight of Selected Objective": w,
                        "Alternative": alt,
                        "Total Score": total_score,
                    }
                )

        df_w = pd.DataFrame(plot_data_w)
        fig_w = px.line(
            df_w,
            x="Weight of Selected Objective",
            y="Total Score",
            color="Alternative",
            color_discrete_map=alt_color_map,
            title=f"Weight Sensitivity for {selected_attr_w['name']}",
            labels={
                "Weight of Selected Objective": f"Weight of {selected_attr_w['name']}",
                "Total Score": "Overall Score",
            },
        )
        fig_w.add_vline(
            x=float(selected_attr_w["weight"]),
            line_dash="dash",
            line_color=NEUTRAL_LINE,
            annotation_text="Current Weight",
            annotation_position="top right",
        )
        fig_w.update_layout(yaxis_range=[-0.02, 1.05], xaxis_range=[-0.02, 1.02], height=440)
        st.plotly_chart(fig_w, use_container_width=True)

    # 2. Objective score sensitivity
    st.subheader("Objective Score Sensitivity")
    st.caption("Test how uncertainty in one alternative's raw score for a selected objective changes the final outcome.")

    col1, col2 = st.columns(2)
    with col1:
        selected_alt_name_s = st.selectbox(
            "Select alternative",
            alt_names,
            key="vft_score_sens_alt",
        )
    with col2:
        selected_attr_name_s = st.selectbox(
            "Select objective to vary",
            [a["name"] for a in attributes],
            key="vft_score_sens_attr",
        )

    selected_attr_s = next((a for a in attributes if a["name"] == selected_attr_name_s), None)

    if selected_attr_s:
        score_range = np.linspace(float(selected_attr_s["min_val"]), float(selected_attr_s["max_val"]), 50)
        other_alts = [a for a in alt_names if a != selected_alt_name_s]

        plot_data_s = []
        for score in score_range:
            new_val = interp_value_from_points(score, selected_attr_s["points"])

            new_total = 0.0
            for attr in attributes:
                if attr["name"] == selected_attr_s["name"]:
                    new_total += new_val * float(attr["weight"])
                else:
                    new_total += alt_value_scores[selected_alt_name_s][attr["name"]] * float(attr["weight"])

            plot_data_s.append(
                {
                    "Raw Score": score,
                    "Alternative": selected_alt_name_s,
                    "Total Score": new_total,
                }
            )

            for other_alt in other_alts:
                plot_data_s.append(
                    {
                        "Raw Score": score,
                        "Alternative": other_alt,
                        "Total Score": base_total_scores[other_alt],
                    }
                )

        df_s = pd.DataFrame(plot_data_s)
        fig_s = px.line(
            df_s,
            x="Raw Score",
            y="Total Score",
            color="Alternative",
            color_discrete_map=alt_color_map,
            title=f"Score Sensitivity for {selected_alt_name_s} on {selected_attr_s['name']}",
            labels={
                "Raw Score": "Raw Score",
                "Total Score": "Overall Score",
            },
        )

        current_raw_score = float(raw_matrix.loc[selected_alt_name_s, selected_attr_s["name"]])
        fig_s.add_vline(
            x=current_raw_score,
            line_dash="dash",
            line_color=NEUTRAL_LINE,
            annotation_text="Current Score",
            annotation_position="top right",
        )
        fig_s.update_layout(yaxis_range=[-0.02, 1.05], height=440)
        st.plotly_chart(fig_s, use_container_width=True)

    # 3. Robustness analysis
    st.subheader("Robustness Analysis")
    st.caption("See which objective weights create the largest swing in total score for a selected alternative.")

    top_alt_name = ranked_alts[0][0] if ranked_alts else alt_names[0]
    selected_alt_name_r = st.selectbox(
        "Select alternative for robustness chart",
        alt_names,
        index=alt_names.index(top_alt_name) if top_alt_name in alt_names else 0,
        key="vft_robust_sens_alt",
    )

    tornado_data = []
    base_score = base_total_scores[selected_alt_name_r]

    for attr in attributes:
        other_attrs = [a for a in attributes if a["name"] != attr["name"]]
        base_other_weights = {a["name"]: float(a["weight"]) for a in other_attrs}
        sum_other_weights = sum(base_other_weights.values())

        w0_score = 0.0
        if sum_other_weights > 0:
            for other_attr in other_attrs:
                proportional_weight = base_other_weights[other_attr["name"]] / sum_other_weights
                w0_score += alt_value_scores[selected_alt_name_r][other_attr["name"]] * proportional_weight
        else:
            if other_attrs:
                equal_weight = 1.0 / len(other_attrs)
                for other_attr in other_attrs:
                    w0_score += alt_value_scores[selected_alt_name_r][other_attr["name"]] * equal_weight

        w1_score = alt_value_scores[selected_alt_name_r][attr["name"]] * 1.0

        min_score = min(w0_score, w1_score)
        max_score = max(w0_score, w1_score)
        spread = max_score - min_score

        tornado_data.append(
            {
                "Objective": attr["name"],
                "Base Score": base_score,
                "Weight0 Score": w0_score,
                "Weight1 Score": w1_score,
                "Min Score": min_score,
                "Max Score": max_score,
                "Spread": spread,
            }
        )

    df_t = pd.DataFrame(tornado_data)
    if not df_t.empty:
        df_t = df_t.sort_values(by="Spread", ascending=True).reset_index(drop=True)

        fig_t = go.Figure()

        fig_t.add_shape(
            type="line",
            x0=base_score,
            y0=-0.5,
            x1=base_score,
            y1=len(df_t) - 0.5,
            line=dict(color=NEUTRAL_LINE, width=2, dash="dash"),
        )

        fig_t.add_trace(
            go.Bar(
                y=df_t["Objective"],
                x=df_t["Max Score"] - df_t["Min Score"],
                base=df_t["Min Score"],
                orientation="h",
                marker_color="#A8DADC",
                hovertemplate=(
                    "Objective: %{y}<br>"
                    "Range Start: %{base:.4f}<br>"
                    "Range Width: %{x:.4f}<extra></extra>"
                ),
                showlegend=False,
            )
        )

        fig_t.add_trace(
            go.Scatter(
                x=df_t["Weight0 Score"],
                y=df_t["Objective"],
                mode="markers",
                marker=dict(size=10, color="#1F4E79"),
                name="Weight = 0",
            )
        )

        fig_t.add_trace(
            go.Scatter(
                x=df_t["Weight1 Score"],
                y=df_t["Objective"],
                mode="markers",
                marker=dict(size=10, color="#2A9D8F"),
                name="Weight = 1",
            )
        )

        fig_t.update_layout(
            title=f"Robustness Tornado Chart for {selected_alt_name_r}",
            xaxis_title="Overall Score",
            yaxis_title="Objective",
            xaxis_range=[0, 1.05],
            height=460,
            margin=dict(l=10, r=10, t=55, b=10),
        )
        st.plotly_chart(fig_t, use_container_width=True)


# -----------------------------------------------------------------------------
# Load base preference data
# -----------------------------------------------------------------------------
prefs = load_prefs(scenario_id)
if not prefs:
    st.info("No preference sets found. Create them in Step 2.")
    st.stop()

pref_ids = [p["preference_set_id"] for p in prefs]
pref_id_to_name = {p["preference_set_id"]: p["name"] for p in prefs}

# -----------------------------------------------------------------------------
# SECTION 1: Sandbox for both methods
# -----------------------------------------------------------------------------
render_common_sandbox_section(
    current_scenario_id=scenario_id,
    prefs_for_scenario=prefs,
    pref_name_map=pref_id_to_name,
    current_method_choice=method_choice,
    current_user_name=user_name,
)

st.divider()

# -----------------------------------------------------------------------------
# SECTION 2: Preference Set Comparison
# -----------------------------------------------------------------------------
st.header("⚖️ Preference Set Comparison")
st.caption(
    "Compare how rankings differ across multiple preference sets within the same scenario, "
    "or across selected preference sets from different scenarios."
)

cmp_mode = st.radio(
    "Comparison mode",
    ["Same scenario - multiple preference sets", "Cross-scenario - selected preference sets"],
    horizontal=True,
    key="cmp_mode_radio",
)

if cmp_mode == "Same scenario - multiple preference sets":
    if len(prefs) < 2:
        st.info("Create at least 2 preference sets in Step 2 to enable comparison.")
    else:
        default_picks = pref_ids[: min(2, len(pref_ids))]
        selected_prefs = st.multiselect(
            "Preference sets to compare (2-5)",
            options=pref_ids,
            default=default_picks,
            max_selections=5,
            format_func=lambda x: pref_id_to_name.get(x, x),
            key=f"cmp_prefs_{scenario_id}",
        )

        if len(selected_prefs) < 2:
            st.warning("Select at least 2 preference sets.")
        else:
            run_method = "topsis" if method_choice == "topsis" else "vft"

            selection_rows = [
                {
                    "scenario_id": scenario_id,
                    "preference_set_id": pid,
                    "comparison_label": pref_id_to_name.get(pid, pid),
                }
                for pid in selected_prefs
            ]

            if st.button("▶ Compare Preference Sets", type="primary", key="btn_cmp_prefs"):
                payload = build_comparison_payload(selection_rows, run_method)
                st.session_state["cmp_result_same"] = payload
                st.rerun()

            cmp = st.session_state.get("cmp_result_same")
            if cmp:
                render_comparison_section(cmp, "pref_comparison.csv")

else:
    section_header("Cross-Scenario Comparison", variant="accent")
    st.caption(
        "Select up to 5 preference sets from different scenarios. Comparison is allowed only when the "
        "underlying alternatives, criteria, and measurement data are identical."
    )

    xs_method = st.radio("Method to compare", ["topsis", "vft"], horizontal=True, key="xs_method")

    all_pref_options = load_all_pref_options(xs_method)
    if not all_pref_options:
        st.info(f"No {xs_method.upper()} preference sets are available for cross-scenario comparison.")
        st.stop()

    option_map: dict[str, dict] = {}
    option_keys = []
    scenario_label_map: dict[str, str] = {}

    for row in all_pref_options:
        key = f"{row['scenario_id']}::{row['preference_set_id']}"
        label = f"{row['decision_title']} | {row['scenario_name']} | {row['preference_name']}"
        option_map[key] = {
            "scenario_id": row["scenario_id"],
            "preference_set_id": row["preference_set_id"],
            "comparison_label": label,
            "scenario_label": f"{row['decision_title']} | {row['scenario_name']}",
        }
        option_keys.append(key)
        scenario_label_map[row["scenario_id"]] = f"{row['decision_title']} | {row['scenario_name']}"

    default_cross = option_keys[: min(2, len(option_keys))]
    selected_option_keys = st.multiselect(
        "Preference sets to compare across scenarios (2-5)",
        options=option_keys,
        default=default_cross,
        max_selections=5,
        format_func=lambda x: option_map[x]["comparison_label"],
        key="xs_pref_multiselect",
    )

    if len(selected_option_keys) < 2:
        st.warning("Select at least 2 preference sets.")
    else:
        selected_rows = [option_map[k] for k in selected_option_keys]
        selected_scenario_ids = [r["scenario_id"] for r in selected_rows]

        valid_inputs, validation_msg = validate_scenarios_comparable(selected_scenario_ids, scenario_label_map)
        if not valid_inputs:
            st.error(validation_msg)
        else:
            st.success("Validation passed. The selected scenarios share the same input structure and measurement data.")

            if st.button("▶ Compare Selected Preference Sets", type="primary", key="btn_cmp_cross_pref_sets"):
                payload = build_comparison_payload(selected_rows, xs_method)
                st.session_state["cmp_result_cross"] = payload
                st.rerun()

            xs_cmp = st.session_state.get("cmp_result_cross")
            if xs_cmp:
                render_comparison_section(xs_cmp, "cross_scenario_preference_comparison.csv")
