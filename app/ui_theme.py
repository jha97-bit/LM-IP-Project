import streamlit as st
import plotly.io as pio
import pandas as pd

BLUE_SCALE = ["#F4F4F4", "#E8EEF3", "#D5E0EA", "#B8CADB", "#90AFC8", "#5B84A6", "#355F85", "#24486B", "#1E3A5F"]
TEAL_SCALE = ["#F1FBF9", "#D8F1EC", "#B8E4DB", "#8FD3C6", "#62C0AF", "#2A9D8F", "#1F8579", "#176A61", "#11514A"]
BLUE_TEAL_SCALE = ["#F4F4F4", "#E8EEF3", "#D4E1E0", "#B8D8D2", "#93C8BD", "#5FB3A4", "#2A9D8F", "#2A6E79", "#1E3A5F"]
DISCRETE_PALETTE = ["#1E3A5F", "#2A9D8F", "#E9C46A", "#5B84A6", "#3B6E9A", "#4AAFA0", "#CDAE5D", "#2F506F", "#6BAFA5", "#A8DADC"]
ALT_BAR_PALETTE = ["#1E3A5F", "#2A9D8F", "#E9C46A", "#5B84A6", "#4AAFA0", "#2F506F", "#CDAE5D", "#A8DADC"]


def section_header(text: str, variant: str = "accent") -> None:
    """
    Render a consistent heading ribbon across pages.

    variant:
      - "solid": teal filled ribbon
      - "accent": light background with teal left bar
      - "gradient": teal→navy gradient ribbon
      - "sub": smaller accent header for subsections
    """
    cls = {
        "solid": "section-header section-header--solid",
        "accent": "section-header section-header--accent",
        "gradient": "section-header section-header--gradient",
        "sub": "section-header section-header--sub",
    }.get(variant, "section-header section-header--accent")
    st.markdown(f"<div class='{cls}'>{text}</div>", unsafe_allow_html=True)


def apply_theme():
    # Force a light Plotly baseline across all pages/charts.
    pio.templates.default = "plotly_white"
    st.markdown(
        """
        <style>
        :root {
          --primary-navy: #1E3A5F;
          --secondary-teal: #2A9D8F;
          --accent-gold: #E9C46A;
          --bg-light: #F8FAFC;
          --surface-light: #FFFFFF;
          --surface-muted: #EEF2F6;
          --text-900: #1E293B;
          --text-700: #475569;
          --border: #E2E8F0;
          --success: #10B981;
          --warning: #FBBF24;
          /* Semantic “negative” without pure red (Streamlit may use for widget chrome) */
          --danger: #5B7C99;
          color-scheme: light;
        }

        /* Align host chrome with teal primary ([theme] primaryColor); navy for our chrome */
        .stApp {
          --primary-color: #1E3A5F !important;
        }

        /* Prevent OS/browser dark mode from forcing dark table surfaces */
        html {
          color-scheme: light !important;
        }

        /* Typography system */
        html, body, .stApp, [data-testid="stAppViewContainer"] {
          font-family: "Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif !important;
        }
        .block-container h1, .block-container h2, .block-container h3,
        [data-testid="stMarkdownContainer"] h1,
        [data-testid="stMarkdownContainer"] h2,
        [data-testid="stMarkdownContainer"] h3 {
          font-family: "Poppins", "Montserrat", "Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif !important;
        }

        /* Readable text selection/highlight using approved palette */
        ::selection {
          background: #A8DADC !important;
          color: #1E293B !important;
        }
        ::-moz-selection {
          background: #A8DADC !important;
          color: #1E293B !important;
        }

        .stApp, [data-testid="stAppViewContainer"] {
          color: var(--text-900) !important;
          background-color: var(--bg-light) !important;
        }

        /*
         * Do NOT hide the app header: when the sidebar is collapsed, Streamlit puts the only
         * “expand sidebar” control (stExpandSidebarButton) and the main menu in stHeader. Hiding
         * the header traps users with no hamburger and no way to reopen the panel.
         * Keep the strip light/minimal instead of display:none.
         */
        header[data-testid="stHeader"],
        .stApp > header {
          display: block !important;
          background: #F1F5F9 !important;
          border-bottom: 1px solid #E2E8F0 !important;
          box-shadow: none !important;
        }
        header[data-testid="stHeader"] [data-testid="stToolbar"],
        .stApp > header [data-testid="stToolbar"] {
          background: transparent !important;
          min-height: 2.75rem !important;
        }
        div[data-testid="stDecoration"] {
          display: none !important;
        }
        [data-testid="stMain"] {
          padding-top: 0 !important;
        }

        .block-container {
          max-width: min(1280px, 96vw) !important;
          padding-top: 24px !important;
          padding-bottom: 24px !important;
          padding-left: clamp(24px, 2.2vw, 32px) !important;
          padding-right: clamp(24px, 2.2vw, 32px) !important;
        }

        /* Global layout compression across pages */
        .block-container h1, .block-container h2, .block-container h3 {
          margin-top: 0.2rem !important;
          margin-bottom: 12px !important;
          color: #1E3A5F !important;
        }
        .block-container h1 {
          font-size: 20px !important;
          font-weight: 600 !important;
          letter-spacing: 0.1px !important;
        }
        .block-container h2, .block-container h3 {
          font-size: 18px !important;
          font-weight: 600 !important;
          border-left: 4px solid #2A9D8F;
          padding-left: 8px !important;
        }
        .block-container p {
          margin-top: 0.15rem !important;
          margin-bottom: 8px !important;
          font-size: 14px !important;
          color: #475569 !important;
        }
        div[data-testid="stCaptionContainer"] {
          margin-top: -2px !important;
          margin-bottom: 8px !important;
        }
        hr, [data-testid="stHorizontalBlock"] hr {
          margin-top: 14px !important;
          margin-bottom: 14px !important;
          border-color: #E2E8F0 !important;
        }
        div[data-testid="stExpander"] {
          margin-top: 6px !important;
          margin-bottom: 12px !important;
        }
        div[data-testid="stForm"] {
          padding-top: 6px !important;
          padding-bottom: 6px !important;
        }
        [data-testid="stVerticalBlock"] > div {
          row-gap: 0.75rem !important;
        }
        [data-testid="stTabs"] {
          margin-top: 4px !important;
        }
        [data-testid="stTabs"] [role="tabpanel"] {
          padding-top: 10px !important;
        }
        [data-testid="stMetric"] {
          padding-top: 8px !important;
          padding-bottom: 8px !important;
        }
        [data-testid="stMetricLabel"] p {
          font-size: 12px !important;
          letter-spacing: 0.4px !important;
          color: #64748B !important;
          text-transform: uppercase !important;
          font-weight: 500 !important;
        }
        [data-testid="stMetricValue"] {
          font-size: 1.05rem !important;
          color: #1E293B !important;
          font-weight: 600 !important;
          line-height: 1.25 !important;
        }

        /* Force sidebar to stay light too */
        [data-testid="stSidebar"], section[data-testid="stSidebar"] {
          background-color: var(--surface-muted) !important;
          border-right: 1px solid var(--border) !important;
          min-width: 200px !important;
          max-width: 220px !important;
          width: 210px !important;
        }
        [data-testid="stSidebar"] *,
        section[data-testid="stSidebar"] * {
          color: var(--text-900) !important;
        }

        /* Labels / captions: keep strong contrast in light theme */
        [data-testid="stMarkdownContainer"] p,
        [data-testid="stCaptionContainer"] p,
        [data-testid="stText"] {
          color: #475569 !important;
        }
        label, legend {
          color: #1E293B !important;
          font-size: 13px !important;
          font-weight: 500 !important;
        }

        div.stButton > button,
        div[data-testid="stFormSubmitButton"] > button {
          border-radius: 10px !important;
          transition: background 0.15s ease, box-shadow 0.12s ease, transform 0.08s ease, border-color 0.15s ease !important;
        }

        /* Primary — raised navy (3D: gradient + inset highlight + depth shadow) */
        button[kind="primary"],
        div.stButton > button[kind="primary"] {
          background: linear-gradient(180deg, #2A4F7A 0%, #1E3A5F 42%, #162E4A 100%) !important;
          color: #FFFFFF !important;
          border: 1px solid #132842 !important;
          box-shadow:
            inset 0 1px 0 rgba(255, 255, 255, 0.14),
            0 4px 12px rgba(30, 58, 95, 0.38),
            0 1px 3px rgba(15, 23, 42, 0.14) !important;
        }

        button[kind="primary"]:hover,
        div.stButton > button[kind="primary"]:hover {
          background: linear-gradient(180deg, #42C4B0 0%, #2A9D8F 42%, #1F8579 100%) !important;
          border-color: #5FD4C0 !important;
          color: #FFFFFF !important;
          filter: brightness(1.04) !important;
          box-shadow:
            inset 0 1px 0 rgba(255, 255, 255, 0.28),
            0 0 0 2px rgba(42, 157, 143, 0.55),
            0 6px 18px rgba(31, 133, 121, 0.48),
            0 2px 5px rgba(15, 23, 42, 0.12) !important;
        }

        /* Focus: teal ring (Base Web often uses theme primary red for :focus) */
        button[kind="primary"]:focus,
        button[kind="primary"]:focus-visible,
        div.stButton > button[kind="primary"]:focus,
        div.stButton > button[kind="primary"]:focus-visible {
          outline: none !important;
          border-color: #8FD3C6 !important;
          box-shadow:
            inset 0 1px 0 rgba(255, 255, 255, 0.18),
            0 0 0 3px rgba(42, 157, 143, 0.65),
            0 4px 14px rgba(30, 58, 95, 0.35) !important;
        }

        button[kind="primary"]:active,
        div.stButton > button[kind="primary"]:active {
          transform: translateY(1px) !important;
          filter: none !important;
          box-shadow:
            inset 0 2px 5px rgba(0, 0, 0, 0.22),
            0 2px 6px rgba(30, 58, 95, 0.28) !important;
        }

        /* Secondary / default — light raised surface */
        button[kind="secondary"],
        div.stButton > button:not([kind="primary"]) {
          background: linear-gradient(180deg, #FFFFFF 0%, #F1F5F9 52%, #E8EEF3 100%) !important;
          color: var(--primary-navy) !important;
          border: 1px solid #B8C4D4 !important;
          box-shadow:
            inset 0 1px 0 rgba(255, 255, 255, 0.95),
            0 3px 8px rgba(15, 23, 42, 0.1),
            0 1px 2px rgba(15, 23, 42, 0.07) !important;
        }

        button[kind="secondary"]:hover,
        div.stButton > button:not([kind="primary"]):hover {
          background: linear-gradient(180deg, #FFFFFF 0%, #E6FAF6 55%, #D8F1EC 100%) !important;
          border-color: #2A9D8F !important;
          color: #176A61 !important;
          box-shadow:
            inset 0 1px 0 rgba(255, 255, 255, 1),
            0 0 0 2px rgba(42, 157, 143, 0.35),
            0 4px 12px rgba(42, 157, 143, 0.2),
            0 2px 4px rgba(15, 23, 42, 0.08) !important;
        }

        button[kind="secondary"]:focus,
        button[kind="secondary"]:focus-visible,
        div.stButton > button:not([kind="primary"]):focus,
        div.stButton > button:not([kind="primary"]):focus-visible {
          outline: none !important;
          border-color: #2A9D8F !important;
          box-shadow:
            inset 0 1px 0 rgba(255, 255, 255, 0.95),
            0 0 0 3px rgba(42, 157, 143, 0.5),
            0 3px 8px rgba(15, 23, 42, 0.1) !important;
        }

        button[kind="secondary"]:active,
        div.stButton > button:not([kind="primary"]):active {
          transform: translateY(1px) !important;
          box-shadow:
            inset 0 2px 4px rgba(148, 163, 184, 0.35),
            0 1px 3px rgba(15, 23, 42, 0.08) !important;
        }

        /* Secondary / default buttons: keep label text dark (fixes white text on light fill) */
        div.stButton > button:not([kind="primary"]) span,
        div.stButton > button:not([kind="primary"]) p,
        button[kind="secondary"] span,
        button[kind="secondary"] p,
        div[data-testid="stFormSubmitButton"] > button:not([kind="primary"]) span,
        div[data-testid="stFormSubmitButton"] > button:not([kind="primary"]) p {
          color: #1E3A5F !important;
          -webkit-text-fill-color: #1E3A5F !important;
        }
        div.stButton > button:not([kind="primary"]):hover span,
        div.stButton > button:not([kind="primary"]):hover p {
          color: #176A61 !important;
          -webkit-text-fill-color: #176A61 !important;
        }

        /* Disabled button readability */
        button:disabled,
        button[disabled],
        div.stButton > button:disabled,
        div.stButton > button[disabled],
        button[kind="primary"]:disabled,
        div.stButton > button[kind="primary"]:disabled,
        button[kind="secondary"]:disabled,
        div.stButton > button[kind="secondary"]:disabled {
          color: #334155 !important;
          -webkit-text-fill-color: #334155 !important;
          opacity: 1 !important;
          background: #E2E8F0 !important;
          border-color: #CBD5E1 !important;
          box-shadow: none !important;
          transform: none !important;
          cursor: not-allowed !important;
        }

        div.stButton > button,
        div[data-testid="stFormSubmitButton"] > button {
          min-height: 40px !important;
          padding: 10px 20px !important;
          border-radius: 6px !important;
          font-size: 14px !important;
          font-weight: 600 !important;
          letter-spacing: 0.5px !important;
          text-transform: uppercase !important;
          display: inline-flex !important;
          align-items: center !important;
          justify-content: center !important;
          gap: 8px !important;
        }

        /* Base inputs */
        [data-testid="stTextInput"] input,
        [data-testid="stNumberInput"] input,
        [data-testid="stTextArea"] textarea {
          height: 40px !important;
          background-color: #ffffff !important;
          color: #1E293B !important;
          border: 1px solid #CBD5E1 !important;
          border-radius: 6px !important;
          font-size: 14px !important;
          padding: 8px 12px !important;
        }

        [data-testid="stTextInput"] input:focus,
        [data-testid="stNumberInput"] input:focus,
        [data-testid="stTextArea"] textarea:focus {
          border-color: var(--secondary-teal) !important;
          box-shadow: 0 0 0 2px rgba(42,157,143,0.16) !important;
        }

        /*
         * Selectbox / multiselect only (scoped). Bare div[data-baseweb="select"] would also match
         * ⋮ → Settings → “Choose app theme” (Base Web select) and block theme changes / clicks.
         */
        [data-testid="stSelectbox"] div[data-baseweb="select"] > div,
        [data-testid="stMultiSelect"] div[data-baseweb="select"] > div {
          background-color: #ffffff !important;
          border: 1px solid #CBD5E1 !important;
          border-radius: 6px !important;
          box-shadow: none !important;
          min-height: 40px !important;
        }

        /* Selected value (closed state) — Base Web can nest text in divs; force dark text */
        [data-testid="stSelectbox"] div[data-baseweb="select"] span,
        [data-testid="stSelectbox"] div[data-baseweb="select"] p,
        [data-testid="stSelectbox"] div[data-baseweb="select"] [role="combobox"],
        [data-testid="stSelectbox"] div[data-baseweb="select"] [role="combobox"] *,
        [data-testid="stMultiSelect"] div[data-baseweb="select"] span,
        [data-testid="stMultiSelect"] div[data-baseweb="select"] p,
        [data-testid="stMultiSelect"] div[data-baseweb="select"] [role="combobox"],
        [data-testid="stMultiSelect"] div[data-baseweb="select"] [role="combobox"] * {
          color: #1E293B !important;
          -webkit-text-fill-color: #1E293B !important;
        }
        [data-testid="stSelectbox"] div[data-baseweb="select"] svg,
        [data-testid="stMultiSelect"] div[data-baseweb="select"] svg {
          fill: #64748B !important;
          color: #64748B !important;
        }

        /* Selectbox single-value text (Base Web uses <input> + inner divs; theme can leave them white on white) */
        [data-testid="stSelectbox"] div[data-baseweb="select"] input,
        [data-testid="stMultiSelect"] div[data-baseweb="select"] input {
          color: #1E293B !important;
          -webkit-text-fill-color: #1E293B !important;
          caret-color: #1E293B !important;
          background-color: #FFFFFF !important;
        }
        [data-testid="stSelectbox"] div[data-baseweb="select"] input::placeholder,
        [data-testid="stMultiSelect"] div[data-baseweb="select"] input::placeholder {
          color: #64748B !important;
          -webkit-text-fill-color: #64748B !important;
          opacity: 1 !important;
        }
        [data-testid="stSelectbox"] div[data-baseweb="select"] [role="combobox"] > div,
        [data-testid="stSelectbox"] div[data-baseweb="select"] [role="group"],
        [data-testid="stMultiSelect"] div[data-baseweb="select"] [role="combobox"] > div,
        [data-testid="stMultiSelect"] div[data-baseweb="select"] [role="group"] {
          color: #1E293B !important;
          -webkit-text-fill-color: #1E293B !important;
        }
        [data-testid="stSelectbox"] label,
        [data-testid="stSelectbox"] [data-testid="stWidgetLabel"] p {
          color: #334155 !important;
        }

        /*
         * Selectbox value in the control “bar” (Streamlit + Base Web often set bodyText near-white for dark UI).
         * Force every text node inside the widget shell — dropdown list is portaled outside this tree.
         */
        [data-testid="stSelectbox"] div[data-baseweb="select"] *:not(svg):not(path):not(circle):not(rect):not(line):not(polyline):not(polygon) {
          color: #0F172A !important;
          -webkit-text-fill-color: #0F172A !important;
        }
        [data-testid="stSelectbox"] div[data-baseweb="select"] input:-webkit-autofill,
        [data-testid="stSelectbox"] div[data-baseweb="select"] input:-webkit-autofill:hover,
        [data-testid="stSelectbox"] div[data-baseweb="select"] input:-webkit-autofill:focus {
          -webkit-text-fill-color: #0F172A !important;
          -webkit-box-shadow: 0 0 0 1000px #FFFFFF inset !important;
          box-shadow: 0 0 0 1000px #FFFFFF inset !important;
        }
        [data-testid="stSelectbox"] div[data-baseweb="select"] input::selection {
          background: #A8DADC !important;
          color: #0F172A !important;
          -webkit-text-fill-color: #0F172A !important;
        }

        /* Multiselect control bar (same bodyText leakage as selectbox) */
        [data-testid="stMultiSelect"] div[data-baseweb="select"] *:not(svg):not(path):not(circle):not(rect):not(line):not(polyline):not(polygon) {
          color: #0F172A !important;
          -webkit-text-fill-color: #0F172A !important;
        }
        [data-testid="stMultiSelect"] div[data-baseweb="select"] input:-webkit-autofill,
        [data-testid="stMultiSelect"] div[data-baseweb="select"] input:-webkit-autofill:focus {
          -webkit-text-fill-color: #0F172A !important;
          -webkit-box-shadow: 0 0 0 1000px #FFFFFF inset !important;
          box-shadow: 0 0 0 1000px #FFFFFF inset !important;
        }

        [data-testid="stSelectbox"] div[data-baseweb="select"] > div:hover,
        [data-testid="stMultiSelect"] div[data-baseweb="select"] > div:hover {
          border-color: rgba(42,157,143,0.75) !important;
        }

        [data-testid="stSelectbox"] div[data-baseweb="select"] > div:focus-within,
        [data-testid="stSelectbox"] div[data-baseweb="select"]:focus-within > div,
        [data-testid="stMultiSelect"] div[data-baseweb="select"] > div:focus-within,
        [data-testid="stMultiSelect"] div[data-baseweb="select"]:focus-within > div,
        [data-testid="stSelectbox"] div[data-baseweb="select"] > div,
        [data-testid="stMultiSelect"] div[data-baseweb="select"] > div {
          box-shadow: none !important;
        }

        [data-testid="stSelectbox"] div[data-baseweb="select"] > div:focus-within,
        [data-testid="stMultiSelect"] div[data-baseweb="select"] > div:focus-within,
        [data-testid="stSelectbox"] div[data-baseweb="select"] > div[aria-expanded="true"],
        [data-testid="stSelectbox"] div[data-baseweb="select"] > div[aria-expanded="true"]:focus-within,
        [data-testid="stMultiSelect"] div[data-baseweb="select"] > div[aria-expanded="true"],
        [data-testid="stMultiSelect"] div[data-baseweb="select"] > div[aria-expanded="true"]:focus-within {
          border-color: var(--secondary-teal) !important;
          box-shadow: 0 0 0 2px rgba(42,157,143,0.16) !important;
        }

        /* Selected chips */
        [data-baseweb="tag"] {
          background: #D8F1EC !important;
          color: #176A61 !important;
          border: 1px solid rgba(42,157,143,0.30) !important;
        }

        [data-baseweb="tag"] span,
        [data-baseweb="tag"] svg {
          color: #176A61 !important;
          fill: #176A61 !important;
        }

        /* Dropdown menu — light surface + dark text (readable) */
        div[role="listbox"] ul,
        ul[role="listbox"] {
          border: 1px solid #CBD5E1 !important;
          box-shadow: 0 12px 28px rgba(15,23,42,0.10) !important;
          background: #FFFFFF !important;
        }

        li[role="option"],
        ul[role="listbox"] li {
          color: #1E293B !important;
        }

        li[role="option"]:hover,
        ul[role="listbox"] li:hover {
          background: #EEF6F5 !important;
        }

        li[role="option"][aria-selected="true"],
        ul[role="listbox"] li[aria-selected="true"] {
          background: #D8F1EC !important;
          color: #0F172A !important;
        }

        /* Base Web popover menus (multiselect / “Create new…” — often dark by default) */
        [data-baseweb="popover"],
        div[data-baseweb="popover"] {
          background-color: #FFFFFF !important;
          color: #1E293B !important;
          box-shadow: 0 12px 28px rgba(15,23,42,0.12) !important;
        }
        [data-baseweb="popover"] li,
        [data-baseweb="popover"] [role="option"],
        [data-baseweb="popover"] div[role="option"],
        ul[data-baseweb="menu"] li {
          color: #1E293B !important;
          background-color: #FFFFFF !important;
        }
        [data-baseweb="popover"] li:hover,
        [data-baseweb="popover"] [role="option"]:hover {
          background-color: #EEF6F5 !important;
        }
        [data-baseweb="popover"] [aria-selected="true"] {
          background-color: #D8F1EC !important;
          color: #0F172A !important;
        }

        /* Nested menus + “Create new…” row (Base Web can leave header/options dark-on-dark) */
        ul[data-baseweb="menu"],
        [data-baseweb="menu"] {
          background-color: #FFFFFF !important;
          border-color: #CBD5E1 !important;
        }
        [data-baseweb="menu"] li,
        [data-baseweb="menu"] [role="option"],
        [data-baseweb="popover"] [data-baseweb="menu"] li,
        [data-baseweb="popover"] [data-baseweb="menu"] [role="option"] {
          color: #1E293B !important;
          -webkit-text-fill-color: #1E293B !important;
          background-color: #FFFFFF !important;
        }
        [data-baseweb="popover"] [data-baseweb="menu"] li:hover,
        [data-baseweb="popover"] [data-baseweb="menu"] [role="option"]:hover {
          background-color: #EEF6F5 !important;
        }

        /*
         * Base Web “Layer” + nested popover wrappers (Select/Multiselect empty / max_selections row).
         * Without this, portaled dropdowns can keep a dark outer box while the message sits on white.
         */
        [data-baseweb="layer"] {
          background: transparent !important;
        }
        [data-baseweb="popover"] > div,
        [data-baseweb="popover"] > div > div {
          background-color: #FFFFFF !important;
          color: #1E293B !important;
        }
        [role="listbox"] {
          background-color: #FFFFFF !important;
          color: #1E293B !important;
        }
        li[role="option"][aria-disabled="true"] {
          background-color: #F1F5F9 !important;
          color: #334155 !important;
          -webkit-text-fill-color: #334155 !important;
          opacity: 1 !important;
        }

        /* Base Web Tooltip (some builds use this instead of menu empty state) */
        [data-baseweb="tooltip"],
        div[data-baseweb="tooltip"] {
          background-color: #FFFFFF !important;
          color: #1E293B !important;
          border: 1px solid #CBD5E1 !important;
          box-shadow: 0 8px 24px rgba(15, 23, 42, 0.12) !important;
        }
        [data-baseweb="tooltip"] div {
          background-color: #FFFFFF !important;
          color: #1E293B !important;
        }

        /* Streamlit Multiselect styled-components: span[aria-disabled='true'] empty / hint rows */
        [data-baseweb="popover"] span[aria-disabled="true"],
        [data-testid="stSelectbox"] div[data-baseweb="select"] span[aria-disabled="true"],
        [data-testid="stMultiSelect"] div[data-baseweb="select"] span[aria-disabled="true"] {
          background: #F1F5F9 !important;
          color: #334155 !important;
        }

        /* Portaled popover: wrapper divs often keep a dark fill — force light (options use li rules above) */
        [data-baseweb="popover"] > div,
        [data-baseweb="popover"] > div > div,
        [data-baseweb="popover"] [data-baseweb="menu"],
        [data-baseweb="popover"] ul[role="listbox"] {
          background-color: #FFFFFF !important;
          color: #1E293B !important;
        }
        [data-baseweb="popover"] * {
          outline-color: #2A9D8F !important;
        }

        /*
         * Multiselect @ max_selections: VirtualDropdown empty state uses nested divs with theme “dark” fills.
         * Force light gray/white on all divs inside the popover, then restore option hover/selected on <li>.
         */
        [data-baseweb="layer"] [data-baseweb="popover"] {
          background-color: #FFFFFF !important;
          box-shadow: 0 12px 28px rgba(15, 23, 42, 0.12) !important;
        }
        .stApp [data-baseweb="popover"] div {
          background-color: #FFFFFF !important;
        }
        .stApp [data-baseweb="popover"] li[role="option"]:hover,
        .stApp [data-baseweb="popover"] li[role="option"]:hover * {
          background-color: #EEF6F5 !important;
        }
        .stApp [data-baseweb="popover"] li[aria-selected="true"],
        .stApp [data-baseweb="popover"] li[aria-selected="true"] * {
          background-color: #D8F1EC !important;
        }

        /* Tabs readability (fixes white-on-light labels) */
        [data-baseweb="tab-list"] {
          gap: 0.35rem;
        }
        [data-baseweb="tab-list"] button {
          background: #E2E8F0 !important;
          color: #334155 !important;
          border: 1px solid #CBD5E1 !important;
          border-radius: 10px 10px 0 0 !important;
          font-weight: 600 !important;
        }
        [data-baseweb="tab-list"] button:hover {
          color: var(--primary-navy) !important;
          border-color: rgba(42,157,143,0.45) !important;
          background: #EEF6F5 !important;
        }
        [data-baseweb="tab-list"] button[aria-selected="true"] {
          color: #ffffff !important;
          border-color: var(--secondary-teal) !important;
          background: var(--secondary-teal) !important;
          box-shadow: 0 2px 8px rgba(42,157,143,0.22) !important;
        }

        /* Checkbox and native radio */
        [data-testid="stCheckbox"] input {
          accent-color: var(--secondary-teal) !important;
        }
        [data-testid="stRadio"] input {
          accent-color: var(--secondary-teal) !important;
        }
        /* Base Web horizontal radio (Streamlit): inner dot may ignore accent-color on <input> */
        [data-testid="stRadio"] [data-baseweb="radio"] div[class*="Inner"] {
          background: var(--secondary-teal) !important;
        }

        /* Sliders — teal fill only (no red primary accent) */
        [data-baseweb="slider"] [role="slider"] {
          background: var(--secondary-teal) !important;
          border-color: #1F8579 !important;
          box-shadow: 0 0 0 2px rgba(42,157,143,0.18) !important;
        }

        [data-baseweb="slider"] > div > div > div {
          background: linear-gradient(90deg, #8FD3C6 0%, #2A9D8F 100%) !important;
        }
        /* Number input stepper buttons */
        [data-testid="stNumberInput"] button {
          color: #F8FAFC !important;
          background: #1E293B !important;
          border: 1px solid #475569 !important;
          border-radius: 4px !important;
          min-width: 36px !important;
          width: 36px !important;
          height: 36px !important;
          font-weight: 600 !important;
        }
        [data-testid="stNumberInput"] button:hover {
          background: #334155 !important;
        }

        /* Default focus ring — teal, not Streamlit primary red */
        *:focus {
          outline-color: var(--secondary-teal) !important;
        }

        /* Metrics and info accents */
        [data-testid="stMetricDelta"],
        [data-testid="stMetricDelta"] svg {
          color: var(--secondary-teal) !important;
          fill: var(--secondary-teal) !important;
        }

        /* Alerts: neutral chrome instead of default red / amber boxes */
        div[data-testid="stAlert"] {
          background-color: #FFF8E1 !important;
          color: #1E293B !important;
          border: 1px solid #E2E8F0 !important;
          border-left: 3px solid #2A9D8F !important;
          padding: 12px 16px !important;
          border-radius: 6px !important;
        }
        div[data-testid="stAlert"] p,
        div[data-testid="stAlert"] span,
        div[data-testid="stAlert"] li {
          color: #1E293B !important;
        }

        /*
         * Glide draws on canvas; theme accent still comes from CSS variables on the host.
         * Streamlit’s default accent for validation/focus can read as red — pin teal palette here.
         */
        div[data-testid="stDataFrame"],
        div[data-testid="stDataEditor"] {
          background: #FFFFFF !important;
          border: 1px solid #E2E8F0 !important;
          border-radius: 8px !important;
          color-scheme: light !important;
          --gdg-accent-color: #2A9D8F !important;
          --gdg-accent-fg: #FFFFFF !important;
          --gdg-accent-light: rgba(42, 157, 143, 0.18) !important;
          --gdg-link-color: #176A61 !important;
        }

        div[data-testid="stTable"],
        div[data-testid="stTable"] > div {
          background: #FFFFFF !important;
        }
        div[data-testid="stTable"] table,
        div[data-testid="stTable"] thead th,
        div[data-testid="stTable"] tbody td,
        div[data-testid="stTable"] tbody th {
          background-color: #FFFFFF !important;
          color: #1E293B !important;
          border-color: #E2E8F0 !important;
        }
        div[data-testid="stTable"] thead th {
          background: #F1F5F9 !important;
          font-weight: 600 !important;
        }

        /* In-cell editor overlay (typed input while editing a cell) */
        div[data-testid="stDataFrame"] textarea,
        div[data-testid="stDataEditor"] textarea,
        div[data-testid="stDataFrame"] input:not([type="hidden"]),
        div[data-testid="stDataEditor"] input:not([type="hidden"]) {
          background-color: #FFFFFF !important;
          color: #1E293B !important;
          -webkit-text-fill-color: #1E293B !important;
          border: 1px solid #CBD5E1 !important;
          caret-color: #1E293B !important;
        }
        /* Dataframe / data editor toolbar (often renders dark with low-contrast icons) */
        [data-testid="stDataFrame"] [data-testid="stElementToolbar"] button,
        [data-testid="stDataEditor"] [data-testid="stElementToolbar"] button,
        [data-testid="stDataFrame"] [data-testid="stElementToolbar"] [role="button"],
        [data-testid="stDataEditor"] [data-testid="stElementToolbar"] [role="button"],
        [data-testid="stElementToolbar"] button,
        [data-testid="stElementToolbar"] [role="button"],
        [data-testid="stToolbar"] button,
        [data-testid="stHeaderToolbar"] button,
        button[kind="header"] {
          background: #F1F5F9 !important;
          color: #1E293B !important;
          border: 1px solid #CBD5E1 !important;
        }
        [data-testid="stDataFrame"] [data-testid="stElementToolbar"] span,
        [data-testid="stDataEditor"] [data-testid="stElementToolbar"] span,
        [data-testid="stDataFrame"] [data-testid="stElementToolbar"] p,
        [data-testid="stDataEditor"] [data-testid="stElementToolbar"] p,
        [data-testid="stElementToolbar"] span,
        [data-testid="stElementToolbar"] p {
          color: #1E293B !important;
          -webkit-text-fill-color: #1E293B !important;
        }
        [data-testid="stDataFrame"] [data-testid="stElementToolbar"] svg,
        [data-testid="stDataEditor"] [data-testid="stElementToolbar"] svg,
        [data-testid="stElementToolbar"] svg,
        [data-testid="stToolbar"] svg,
        [data-testid="stHeaderToolbar"] svg,
        button[kind="header"] svg {
          fill: #1E293B !important;
          color: #1E293B !important;
        }

        /* st.download_button secondary styling (e.g. “Download as CSV” near dataframes) */
        [data-testid="stDownloadButton"] button,
        [data-testid="stDownloadButton"] a {
          background: #F1F5F9 !important;
          color: #1E293B !important;
          border: 1px solid #CBD5E1 !important;
        }
        [data-testid="stDownloadButton"] button span,
        [data-testid="stDownloadButton"] button p,
        [data-testid="stDownloadButton"] a span {
          color: #1E293B !important;
          -webkit-text-fill-color: #1E293B !important;
        }
        [data-testid="stDownloadButton"] svg {
          fill: #1E293B !important;
        }

        /*
         * st.progress (Base Web): paint the track + value bar explicitly.
         * Do not use [data-testid="stProgress"] > div > div > div { teal } — it often colors the
         * full-width wrapper so the “remaining” step area disappears.
         */
        [data-testid="stProgress"] [data-baseweb="progress-bar"] {
          background-color: #E2E8F0 !important;
          border-radius: 999px !important;
        }
        [data-testid="stProgress"] [data-baseweb="progress-bar"] [role="progressbar"] {
          background-color: #E2E8F0 !important;
        }
        [data-testid="stProgress"] [data-baseweb="progress-bar"] [role="progressbar"] > div:last-child {
          background-color: #2A9D8F !important;
          background-image: none !important;
        }

        /* Sidebar step bar (custom HTML in sidebar_nav — not st.progress) */
        .mcda-sidebar-progress-wrap {
          margin: 0 0 10px 0;
        }
        .mcda-sidebar-progress-track {
          height: 8px;
          width: 100%;
          border-radius: 999px;
          background: #E2E8F0;
          overflow: hidden;
          box-shadow: inset 0 1px 2px rgba(15, 23, 42, 0.06);
        }
        .mcda-sidebar-progress-fill {
          height: 100%;
          border-radius: 999px;
          background: linear-gradient(90deg, #3CB8A8 0%, #2A9D8F 55%, #1E3A5F 100%);
          transition: width 0.35s ease;
        }

        /*
         * Segmented control (st.segmented_control): Streamlit swaps button *kind*, not aria-pressed.
         * Inactive: data-testid="stBaseButton-segmented_control"
         * Active:   data-testid="stBaseButton-segmented_controlActive"
         */
        [data-testid="stButtonGroup"] button[data-testid="stBaseButton-segmented_control"],
        [data-baseweb="button-group"] button[data-testid="stBaseButton-segmented_control"] {
          outline: none !important;
          background: linear-gradient(180deg, #F8FAFC 0%, #F1F5F9 100%) !important;
          background-color: #F1F5F9 !important;
          color: #334155 !important;
          border-color: #CBD5E1 !important;
          box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.92) !important;
        }
        [data-testid="stButtonGroup"] button[data-testid="stBaseButton-segmented_control"] span,
        [data-testid="stButtonGroup"] button[data-testid="stBaseButton-segmented_control"] p,
        [data-baseweb="button-group"] button[data-testid="stBaseButton-segmented_control"] span,
        [data-baseweb="button-group"] button[data-testid="stBaseButton-segmented_control"] p {
          color: #334155 !important;
          -webkit-text-fill-color: #334155 !important;
        }
        [data-testid="stButtonGroup"] button[data-testid="stBaseButton-segmented_controlActive"],
        [data-baseweb="button-group"] button[data-testid="stBaseButton-segmented_controlActive"] {
          outline: none !important;
          z-index: 2 !important;
          background: linear-gradient(180deg, #3CB8A8 0%, #2A9D8F 52%, #238B7E 100%) !important;
          background-color: #2A9D8F !important;
          color: #FFFFFF !important;
          border-color: #1F8579 !important;
          box-shadow:
            inset 0 1px 0 rgba(255, 255, 255, 0.22),
            0 2px 8px rgba(23, 106, 97, 0.38) !important;
        }
        [data-testid="stButtonGroup"] button[data-testid="stBaseButton-segmented_controlActive"] span,
        [data-testid="stButtonGroup"] button[data-testid="stBaseButton-segmented_controlActive"] p,
        [data-baseweb="button-group"] button[data-testid="stBaseButton-segmented_controlActive"] span,
        [data-baseweb="button-group"] button[data-testid="stBaseButton-segmented_controlActive"] p {
          color: #FFFFFF !important;
          -webkit-text-fill-color: #FFFFFF !important;
        }
        [data-testid="stButtonGroup"] button[data-testid="stBaseButton-segmented_control"]:focus-visible,
        [data-testid="stButtonGroup"] button[data-testid="stBaseButton-segmented_controlActive"]:focus-visible,
        [data-baseweb="button-group"] button[data-testid="stBaseButton-segmented_control"]:focus-visible,
        [data-baseweb="button-group"] button[data-testid="stBaseButton-segmented_controlActive"]:focus-visible {
          outline: 2px solid #2A9D8F !important;
          outline-offset: 2px !important;
        }

        /* Card containers for input sections */
        .input-card {
          background: var(--surface-light);
          border: 1px solid var(--border);
          border-radius: 12px;
          padding: 16px 20px;
          box-shadow: 0 1px 2px rgba(30,58,95,0.06);
          min-height: 100%;
        }

        /* Section header ribbons */
        .section-header {
          width: 100%;
          box-sizing: border-box;
          margin: 6px 0 10px 0;
          letter-spacing: 0.3px;
        }
        .section-header--solid {
          background-color: var(--secondary-teal);
          color: #FFFFFF;
          font-family: "Poppins", "Montserrat", "Inter", sans-serif;
          font-size: 18px;
          font-weight: 600;
          padding: 10px 16px;
          border-radius: 6px;
        }
        .section-header--accent {
          background-color: #F1F5F9;
          border-left: 6px solid var(--secondary-teal);
          color: var(--primary-navy);
          font-family: "Poppins", "Montserrat", "Inter", sans-serif;
          font-size: 18px;
          font-weight: 600;
          padding: 12px 16px;
          border-radius: 6px;
        }
        .section-header--gradient {
          background: linear-gradient(90deg, var(--secondary-teal) 0%, var(--primary-navy) 100%);
          color: #FFFFFF;
          font-family: "Montserrat", "Poppins", "Inter", sans-serif;
          font-size: 18px;
          font-weight: 600;
          padding: 10px 20px;
          border-radius: 6px;
        }
        .section-header--sub {
          background-color: #F1F5F9;
          border-left: none;
          border-bottom: 2px solid rgba(42, 157, 143, 0.35);
          color: var(--primary-navy);
          font-family: "Poppins", "Montserrat", "Inter", sans-serif;
          font-size: 16px;
          font-weight: 600;
          padding: 10px 14px;
          border-radius: 6px;
          margin-top: 4px;
        }

        /* Compact label-left, input-right rows (used on Results selectors) */
        .run-form-row {
          display: grid;
          grid-template-columns: 140px minmax(0, 1fr);
          align-items: center;
          column-gap: 16px;
          margin-bottom: 10px;
        }
        .run-form-label {
          font-size: 13px;
          font-weight: 500;
          color: #1E293B;
          white-space: nowrap;
        }
        .run-form-row > div[data-baseweb="select"],
        .run-form-row [data-testid="stMultiSelect"] {
          width: 100%;
        }

        /* Plotly chart container + text contrast */
        [data-testid="stPlotlyChart"] {
          background: #FFFFFF !important;
          border: 1px solid #E2E8F0 !important;
          border-radius: 6px !important;
          box-shadow: 0 1px 3px rgba(0,0,0,0.08) !important;
          padding: 10px !important;
        }
        [data-testid="stPlotlyChart"] .js-plotly-plot .plotly .xtick text,
        [data-testid="stPlotlyChart"] .js-plotly-plot .plotly .ytick text,
        [data-testid="stPlotlyChart"] .js-plotly-plot .plotly .gtitle,
        [data-testid="stPlotlyChart"] .js-plotly-plot .plotly .xtitle,
        [data-testid="stPlotlyChart"] .js-plotly-plot .plotly .ytitle,
        [data-testid="stPlotlyChart"] .js-plotly-plot .plotly .legend text,
        [data-testid="stPlotlyChart"] .js-plotly-plot .plotly .textpoint text {
          fill: #334155 !important;
          color: #334155 !important;
          font-size: 13px !important;
        }
        [data-testid="stPlotlyChart"] .js-plotly-plot .plotly .xgrid,
        [data-testid="stPlotlyChart"] .js-plotly-plot .plotly .ygrid {
          stroke: #CBD5E1 !important;
          stroke-opacity: 0.5 !important;
        }
        [data-testid="stPlotlyChart"] .hoverlayer .hovertext {
          fill: #FFFFFF !important;
        }
        [data-testid="stPlotlyChart"] .hoverlayer .bg {
          fill: #2A9D8F !important;
          fill-opacity: 0.98 !important;
        }
        [data-testid="stPlotlyChart"] .js-plotly-plot .plotly .bg {
          fill: #FFFFFF !important;
        }

        /* Ensure key action button text has strong contrast */
        div.stButton > button[kind="primary"] span,
        div.stButton > button[kind="primary"] p,
        div[data-testid="stFormSubmitButton"] > button span {
          color: #FFFFFF !important;
          -webkit-text-fill-color: #FFFFFF !important;
          font-weight: 600 !important;
        }

        /* Sidebar nav polish */
        [data-testid="stSidebar"] a, [data-testid="stSidebar"] p {
          font-size: 12.5px !important;
          letter-spacing: 0.45px !important;
        }
        [data-testid="stSidebar"] a {
          text-transform: uppercase !important;
          font-weight: 600 !important;
          padding-top: 2px !important;
          padding-bottom: 2px !important;
        }
        .sidebar-active-item {
          background: #D8F1EC;
          border-left: 4px solid var(--secondary-teal);
          border-radius: 6px;
          padding: 6px 8px;
          margin-bottom: 4px;
          font-size: 12.5px;
          letter-spacing: 0.45px;
          text-transform: uppercase;
          font-weight: 700;
          color: #176A61 !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # Global, one-time rendering guards so charts/tables cannot fall back to dark mode.
    if not getattr(st, "_mcda_light_wrapped", False):
        _orig_plotly_chart = st.plotly_chart
        _orig_dataframe = st.dataframe

        def _force_light_plotly(fig, **kwargs):
            if hasattr(fig, "update_layout"):
                fig.update_layout(
                    template="plotly_white",
                    paper_bgcolor="#FFFFFF",
                    plot_bgcolor="#F8FAFC",
                    font=dict(color="#334155"),
                )
            return _orig_plotly_chart(fig, **kwargs)

        def _force_light_dataframe(data=None, **kwargs):
            if isinstance(data, pd.DataFrame):
                data = (
                    data.style.set_table_styles(
                        [
                            {"selector": "table", "props": [("background-color", "#FFFFFF"), ("color", "#1E293B")]},
                            {"selector": "thead th", "props": [("background-color", "#F1F5F9"), ("color", "#1E293B"), ("font-weight", "700")]},
                            {"selector": "tbody td", "props": [("background-color", "#FFFFFF"), ("color", "#1E293B"), ("border-bottom", "1px solid #E2E8F0")]},
                        ]
                    )
                )
            return _orig_dataframe(data, **kwargs)

        st.plotly_chart = _force_light_plotly
        st.dataframe = _force_light_dataframe
        st._mcda_light_wrapped = True
