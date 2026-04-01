import bootstrap  # noqa: F401

import streamlit as st
from app.ui_theme import apply_theme, BLUE_SCALE, TEAL_SCALE, BLUE_TEAL_SCALE, DISCRETE_PALETTE, section_header
import pandas as pd
from app.sidebar_nav import render_sidebar
from sqlalchemy import text
from persistence.engine import get_engine, ping_db

st.set_page_config(
    page_title="MCDA Decision Tool",
    page_icon="M",
    layout="wide",
    initial_sidebar_state="expanded",
)
apply_theme()

# ─── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  /* Card-like containers */
  .method-card {
    background: #f0f4fa;
    border: 1px solid rgba(49,130,206,0.25);
    border-radius: 12px;
    padding: 1.5rem;
    height: 100%;
    transition: border-color 0.2s;
    color: #1a202c !important;
  }
  .method-card:hover { border-color: rgba(49,130,206,0.6); }
  .method-card h3 { margin-top: 0; color: #1a365d !important; }
  .method-card p { color: #2d3748 !important; }
  .method-card b { color: #1a202c !important; }
  .method-card ol { color: #2d3748 !important; }
  .method-card li { color: #2d3748 !important; }

  .stat-card {
    background: linear-gradient(135deg, rgba(49,130,206,0.08) 0%, rgba(49,130,206,0.02) 100%);
    border: 1px solid rgba(49,130,206,0.15);
    border-radius: 10px;
    padding: 1rem 1.2rem;
    text-align: center;
  }
  .stat-num {
    font-size: 2.2rem;
    font-weight: 700;
    color: #2b6cb0;
    line-height: 1;
  }
  .stat-lbl { font-size: 0.8rem; color: #718096; margin-top: 0.3rem; }

  .badge-topsis {
    display: inline-block;
    background: #ebf8ff;
    color: #2b6cb0;
    border: 1px solid #bee3f8;
    border-radius: 20px;
    padding: 2px 10px;
    font-size: 0.75rem;
    font-weight: 600;
  }
  .badge-vft {
    display: inline-block;
    background: #f0fff4;
    color: #276749;
    border: 1px solid #9ae6b4;
    border-radius: 20px;
    padding: 2px 10px;
    font-size: 0.75rem;
    font-weight: 600;
  }
  .recent-item {
    display: flex;
    align-items: center;
    gap: 0.8rem;
    padding: 0.6rem 0;
    border-bottom: 1px solid rgba(0,0,0,0.06);
  }
  .recent-item:last-child { border-bottom: none; }
</style>
""", unsafe_allow_html=True)

# ─── Session defaults ───────────────────────────────────────────────────────────
st.session_state.setdefault("user_name", "")
st.session_state.setdefault("decision_id", None)
st.session_state.setdefault("scenario_id", None)
st.session_state.setdefault("method_choice", None)

render_sidebar("streamlit_app.py")

# ─── Header (ribbon + tagline) ────────────────────────────────────────────────
st.markdown(
    """
    <style>
      .mcda-home-ribbon-wrap { margin-bottom: 0.35rem; }
      .mcda-home-tagline {
        font-family: "Inter", sans-serif;
        font-size: 14px;
        color: #475569;
        margin: 0 0 12px 0;
        padding-left: 2px;
      }
    </style>
    """,
    unsafe_allow_html=True,
)
st.markdown('<div class="mcda-home-ribbon-wrap">', unsafe_allow_html=True)
section_header("MCDA Decision Tool", variant="gradient")
st.markdown("</div>", unsafe_allow_html=True)
st.markdown(
    '<p class="mcda-home-tagline">Multi-Criteria Decision Analysis · TOPSIS &amp; VFT · Enterprise workflow</p>',
    unsafe_allow_html=True,
)

# DB status indicator
try:
    db_ok = ping_db()
except Exception:
    db_ok = False

if db_ok:
    st.success("Database connected", icon=None)
else:
    st.warning("Database not reachable — check DATABASE_URL in your .env file")

# ─── Identity + Quick Start ────────────────────────────────────────────────────
left_col, right_col = st.columns([2, 1], gap="large")

with left_col:
    st.subheader("Who Are You?")
    st.caption("Your name will be recorded on every run for traceability.")
    user_name = st.text_input(
        "Your name",
        value=st.session_state["user_name"],
        placeholder="e.g. Atharva, Ritika...",
        label_visibility="collapsed",
    )
    st.session_state["user_name"] = (user_name or "").strip()

    st.markdown("### START A NEW ANALYSIS")
    col_t, col_v, col_h = st.columns(3)
    with col_t:
        if st.button(
            "TOPSIS",
            type="primary",
            use_container_width=True,
            disabled=not st.session_state["user_name"],
        ):
            st.session_state["method_choice"] = "topsis"
            st.switch_page("pages/1_decision_setup.py")

    with col_v:
        if st.button(
            "VFT",
            type="primary",
            use_container_width=True,
            disabled=not st.session_state["user_name"],
        ):
            st.session_state["method_choice"] = "vft"
            st.switch_page("pages/1_decision_setup.py")

    with col_h:
        if st.button(
            "HISTORY",
            use_container_width=True,
            disabled=not db_ok,
        ):
            st.switch_page("pages/7_history.py")

    if not st.session_state["user_name"]:
        st.caption("Enter your name to enable analysis buttons.")

with right_col:
    # Live stats
    if db_ok:
        try:
            engine = get_engine()
            with engine.begin() as conn:
                n_dec = conn.execute(text("SELECT COUNT(*) FROM decisions")).scalar() or 0
                n_scen = conn.execute(text("SELECT COUNT(*) FROM scenarios")).scalar() or 0
                n_runs = conn.execute(text("SELECT COUNT(*) FROM runs")).scalar() or 0
                n_topsis = conn.execute(text("SELECT COUNT(*) FROM runs WHERE method='topsis'")).scalar() or 0
                n_vft = conn.execute(text("SELECT COUNT(*) FROM runs WHERE method='vft'")).scalar() or 0
        except Exception:
            n_dec = n_scen = n_runs = n_topsis = n_vft = 0

        st.markdown("### 📊 Workspace Summary")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(f"""
            <div class="stat-card">
              <div class="stat-num">{n_dec}</div>
              <div class="stat-lbl">Decisions</div>
            </div>
            """, unsafe_allow_html=True)
        with c2:
            st.markdown(f"""
            <div class="stat-card">
              <div class="stat-num">{n_scen}</div>
              <div class="stat-lbl">Scenarios</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("")
        c3, c4, c5 = st.columns(3)
        with c3:
            st.markdown(f"""
            <div class="stat-card">
              <div class="stat-num">{n_topsis}</div>
              <div class="stat-lbl">TOPSIS Runs</div>
            </div>
            """, unsafe_allow_html=True)
        with c4:
            st.markdown(f"""
            <div class="stat-card">
              <div class="stat-num">{n_vft}</div>
              <div class="stat-lbl">VFT Runs</div>
            </div>
            """, unsafe_allow_html=True)
        with c5:
            st.markdown(f"""
            <div class="stat-card">
              <div class="stat-num">{n_runs}</div>
              <div class="stat-lbl">Total Runs</div>
            </div>
            """, unsafe_allow_html=True)

# ─── Methods overview ─────────────────────────────────────────────────────────
st.markdown("### ANALYSIS METHODS")
mc1, mc2 = st.columns(2, gap="large")

with mc1:
    st.markdown("""
    <div class="method-card">
      <h3>TOPSIS</h3>
      <span class="badge-topsis">Technique for Order of Preference by Similarity to Ideal Solution</span>
      <p style="margin-top: 1rem;">Ranks alternatives by measuring their distance from the ideal best
      and ideal worst solutions. Best suited when you have quantitative data with clear benefit/cost directions.</p>
      <b>Steps:</b>
      <ol style="margin:0; padding-left: 1.2rem;">
        <li>Normalize the performance matrix</li>
        <li>Apply criterion weights</li>
        <li>Compute ideal best (PIS) and ideal worst (NIS)</li>
        <li>Calculate Euclidean distances S+ and S−</li>
        <li>Compute closeness score C* and rank</li>
      </ol>
    </div>
    """, unsafe_allow_html=True)

with mc2:
    st.markdown("""
    <div class="method-card">
      <h3>VFT — Value Function Transformation</h3>
      <span class="badge-vft">Multi-Attribute Value Theory</span>
      <p style="margin-top: 1rem;">Converts raw measurements into utility scores (0–1) using user-defined
      value functions. Supports linear and custom piecewise-linear functions. Ideal when preferences
      are non-linear or when you want precise control over scoring.</p>
      <b>Steps:</b>
      <ol style="margin:0; padding-left: 1.2rem;">
        <li>Define a value function per criterion</li>
        <li>Convert raw x to utility u(x) ∈ [0, 1]</li>
        <li>Apply swing weights</li>
        <li>Sum weighted utilities → total score</li>
        <li>Rank alternatives</li>
      </ol>
    </div>
    """, unsafe_allow_html=True)

# ─── Recent Activity ──────────────────────────────────────────────────────────
if db_ok:
    st.markdown("### RECENT RUNS")
    try:
        engine = get_engine()
        with engine.begin() as conn:
            recent = conn.execute(
                text("""
                    SELECT r.run_id::text, r.method, r.executed_at, r.executed_by,
                           r.run_label, s.name AS scenario_name, d.title AS decision_title
                    FROM runs r
                    JOIN scenarios s ON s.scenario_id = r.scenario_id
                    JOIN decisions d ON d.decision_id = s.decision_id
                    ORDER BY r.executed_at DESC
                    LIMIT 8
                """)
            ).mappings().all()

        if recent:
            for run in recent:
                if run["method"] == "topsis":
                    badge = '<span class="badge-topsis">TOPSIS</span>'
                elif run["method"] == "vft":
                    badge = '<span class="badge-vft">VFT</span>'
                else:
                    badge = '<span style="font-size:0.75rem;color:#64748B;font-weight:600;">OTHER</span>'
                label = run.get("run_label") or run["run_id"][:12] + "…"
                by = f" · {run['executed_by']}" if run.get("executed_by") else ""
                ts = str(run["executed_at"])[:16]

                st.markdown(f"""
                <div class="recent-item">
                  {badge}
                  <div style="flex:1">
                    <b>{run['decision_title']}</b> → {run['scenario_name']}
                    <span style="color:#718096; font-size:0.85rem"> · {label}{by}</span>
                  </div>
                  <span style="color:#a0aec0; font-size:0.8rem">{ts}</span>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No runs yet. Start an analysis above.")
    except Exception as e:
        st.warning(f"Could not load recent runs: {e}")

# ─── Governance note ──────────────────────────────────────────────────────────
st.markdown("### GOVERNANCE AND AUDITABILITY")
g1, g2, g3 = st.columns(3)
with g1:
    st.markdown("**Database as source of truth**")
    st.caption("All inputs, runs, and computed artifacts are stored in PostgreSQL.")
with g2:
    st.markdown("**Full run traceability**")
    st.caption("Each run records: who ran it, when, with which weights, and the input fingerprint.")
with g3:
    st.markdown("**Scenario sharing**")
    st.caption("Export any scenario as a .mcda file to share with colleagues. They can import and view your exact data.")
