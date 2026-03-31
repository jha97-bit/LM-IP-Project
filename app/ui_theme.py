import streamlit as st
import plotly.io as pio
import pandas as pd

BLUE_SCALE = ["#F4F4F4", "#E8EEF3", "#D5E0EA", "#B8CADB", "#90AFC8", "#5B84A6", "#355F85", "#24486B", "#1E3A5F"]
TEAL_SCALE = ["#F1FBF9", "#D8F1EC", "#B8E4DB", "#8FD3C6", "#62C0AF", "#2A9D8F", "#1F8579", "#176A61", "#11514A"]
BLUE_TEAL_SCALE = ["#F4F4F4", "#E8EEF3", "#D4E1E0", "#B8D8D2", "#93C8BD", "#5FB3A4", "#2A9D8F", "#2A6E79", "#1E3A5F"]
DISCRETE_PALETTE = ["#1E3A5F", "#2A9D8F", "#E9C46A", "#5B84A6", "#3B6E9A", "#4AAFA0", "#CDAE5D", "#2F506F", "#6BAFA5", "#A8DADC"]
ALT_BAR_PALETTE = ["#1E3A5F", "#2A9D8F", "#E9C46A", "#5B84A6", "#4AAFA0", "#2F506F", "#CDAE5D", "#A8DADC"]

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
          color-scheme: light;
        }

        /* Prevent OS/browser dark mode from forcing dark table surfaces */
        html {
          color-scheme: light !important;
        }

        html, body, .stApp, [data-testid="stAppViewContainer"] {
          font-family: "Montserrat", "Poppins", "Roboto", "Open Sans", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif !important;
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
        div[data-testid="stFormSubmitButton"] > button,
        button[kind="primary"],
        button[kind="secondary"] {
          border-radius: 10px !important;
          border: 1px solid rgba(37,99,235,0.25) !important;
          transition: all 0.15s ease !important;
          box-shadow: none !important;
        }

        button[kind="primary"],
        div.stButton > button[kind="primary"] {
          background: linear-gradient(135deg, var(--secondary-teal) 0%, #1F8579 100%) !important;
          color: #FFFFFF !important;
          border-color: var(--secondary-teal) !important;
        }

        button[kind="primary"]:hover,
        div.stButton > button[kind="primary"]:hover {
          background: linear-gradient(135deg, #1F8579 0%, #176A61 100%) !important;
          border-color: #176A61 !important;
          color: #FFFFFF !important;
        }

        button[kind="secondary"],
        div.stButton > button:not([kind="primary"]) {
          background: var(--surface-light) !important;
          color: var(--primary-navy) !important;
          border-color: rgba(30,58,95,0.25) !important;
        }

        button[kind="secondary"]:hover,
        div.stButton > button:not([kind="primary"]):hover {
          background: #E8EEF3 !important;
          border-color: rgba(42,157,143,0.45) !important;
          color: #24486B !important;
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

        /* Selectbox and multiselect shell */
        div[data-baseweb="select"] > div {
          background-color: #ffffff !important;
          border: 1px solid #CBD5E1 !important;
          border-radius: 6px !important;
          box-shadow: none !important;
          min-height: 40px !important;
        }

        /* Selected value (closed state) */
        div[data-baseweb="select"] span {
          color: var(--text-900) !important;
        }

        div[data-baseweb="select"] > div:hover {
          border-color: rgba(42,157,143,0.75) !important;
        }

        div[data-baseweb="select"] > div:focus-within,
        div[data-baseweb="select"]:focus-within > div,
        [data-testid="stSelectbox"] div[data-baseweb="select"] > div,
        [data-testid="stMultiSelect"] div[data-baseweb="select"] > div {
          box-shadow: none !important;
        }

        [data-testid="stSelectbox"] div[data-baseweb="select"] > div:focus-within,
        [data-testid="stMultiSelect"] div[data-baseweb="select"] > div:focus-within,
        div[data-baseweb="select"] > div[aria-expanded="true"],
        div[data-baseweb="select"] > div[aria-expanded="true"]:focus-within {
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

        /* Dropdown menu and selected items */
        div[role="listbox"] ul,
        ul[role="listbox"] {
          border: 1px solid #475569 !important;
          box-shadow: 0 12px 28px rgba(15,23,42,0.10) !important;
          background: #1F2937 !important;
        }

        li[role="option"],
        ul[role="listbox"] li {
          color: #F1F5F9 !important;
        }

        li[role="option"]:hover,
        ul[role="listbox"] li:hover {
          background: rgba(42,157,143,0.15) !important;
        }

        li[role="option"][aria-selected="true"],
        ul[role="listbox"] li[aria-selected="true"] {
          background: rgba(42,157,143,0.15) !important;
          color: #E2E8F0 !important;
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

        /* Checkbox and radio */
        [data-testid="stCheckbox"] input,
        [data-testid="stRadio"] input {
          accent-color: var(--secondary-teal) !important;
        }

        /* Sliders */
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

        /* Focus ring cleanup */
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

        /* Data editor readability and softer row rhythm */
        div[data-testid="stDataFrame"] [role="columnheader"] {
          font-size: 0.95rem !important;
          font-weight: 700 !important;
          color: var(--primary-navy) !important;
          background: #E8EEF3 !important;
        }
        div[data-testid="stDataFrame"] [role="gridcell"] {
          font-size: 0.93rem !important;
          line-height: 1.5 !important;
          color: var(--text-900) !important;
          background: #FFFFFF !important;
          border-color: #E2E8F0 !important;
        }
        div[data-testid="stDataFrame"] [role="row"]:nth-child(even) [role="gridcell"] {
          background: #FAFCFF !important;
        }
        div[data-testid="stDataFrame"] [role="row"]:hover [role="gridcell"] {
          background: #EEF6F5 !important;
        }

        /* Force light theme for all Streamlit dataframe/table widgets */
        div[data-testid="stDataFrame"],
        div[data-testid="stDataFrame"] * {
          color: #1E293B !important;
        }
        div[data-testid="stDataFrame"] [role="grid"],
        div[data-testid="stDataFrame"] [data-testid="stDataFrameResizable"],
        div[data-testid="stDataFrame"] .glideDataEditor,
        div[data-testid="stDataFrame"] .gdg-container,
        div[data-testid="stDataFrame"] .gdg,
        div[data-testid="stDataFrame"] .gdg-outer {
          background: #FFFFFF !important;
        }
        div[data-testid="stDataFrame"] [role="rowheader"],
        div[data-testid="stDataFrame"] .gdg-cell,
        div[data-testid="stDataFrame"] .gdg-cell * {
          background: #FFFFFF !important;
          color: #1E293B !important;
          border-color: #E2E8F0 !important;
        }
        div[data-testid="stDataFrame"] [role="columnheader"],
        div[data-testid="stDataFrame"] .gdg-header,
        div[data-testid="stDataFrame"] .gdg-header * {
          background: #F1F5F9 !important;
          color: #1E293B !important;
          border-color: #E2E8F0 !important;
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

        /* Dataframe outer shell (some Streamlit builds paint this dark) */
        div[data-testid="stDataFrame"] {
          background: #FFFFFF !important;
          border: 1px solid #E2E8F0 !important;
          border-radius: 8px !important;
        }
        div[data-testid="stDataFrame"] > div {
          background: #FFFFFF !important;
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
