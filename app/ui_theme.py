import streamlit as st

BLUE_SCALE = ["#EFF6FF", "#DBEAFE", "#BFDBFE", "#93C5FD", "#60A5FA", "#3B82F6", "#2563EB", "#1D4ED8", "#1E40AF"]
TEAL_SCALE = ["#F0FDFA", "#CCFBF1", "#99F6E4", "#5EEAD4", "#2DD4BF", "#14B8A6", "#0D9488", "#0F766E", "#115E59"]
BLUE_TEAL_SCALE = ["#EFF6FF", "#DBEAFE", "#BFDBFE", "#93C5FD", "#60A5FA", "#38BDF8", "#14B8A6", "#0D9488", "#0F766E"]
DISCRETE_PALETTE = ["#1D4ED8", "#0F766E", "#5B21B6", "#0EA5E9", "#2563EB", "#14B8A6", "#4338CA", "#0891B2", "#6366F1", "#06B6D4"]
ALT_BAR_PALETTE = ["#1D4ED8", "#2563EB", "#3B82F6", "#60A5FA", "#93C5FD", "#0F766E", "#14B8A6", "#5EEAD4"]

def apply_theme():
    st.markdown(
        """
        <style>
        :root {
          --blue-50: #EFF6FF;
          --blue-100: #DBEAFE;
          --blue-200: #BFDBFE;
          --blue-300: #93C5FD;
          --blue-400: #60A5FA;
          --blue-500: #3B82F6;
          --blue-600: #2563EB;
          --blue-700: #1D4ED8;
          --blue-800: #1E40AF;
          --teal-500: #14B8A6;
          --teal-700: #0F766E;
          --text-900: #0F172A;
        }

        .stApp, [data-testid="stAppViewContainer"] {
          color: var(--text-900) !important;
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
          background: linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%) !important;
          color: #FFFFFF !important;
          border-color: #1D4ED8 !important;
        }

        button[kind="primary"]:hover,
        div.stButton > button[kind="primary"]:hover {
          background: linear-gradient(135deg, #1D4ED8 0%, #1E40AF 100%) !important;
          border-color: #1E40AF !important;
          color: #FFFFFF !important;
        }

        button[kind="secondary"],
        div.stButton > button:not([kind="primary"]) {
          background: #EFF6FF !important;
          color: #1D4ED8 !important;
          border-color: rgba(37,99,235,0.28) !important;
        }

        button[kind="secondary"]:hover,
        div.stButton > button:not([kind="primary"]):hover {
          background: #DBEAFE !important;
          border-color: rgba(29,78,216,0.40) !important;
          color: #1E40AF !important;
        }

        /* Base inputs */
        [data-testid="stTextInput"] input,
        [data-testid="stNumberInput"] input,
        [data-testid="stTextArea"] textarea {
          border-color: rgba(148,163,184,0.7) !important;
        }

        [data-testid="stTextInput"] input:focus,
        [data-testid="stNumberInput"] input:focus,
        [data-testid="stTextArea"] textarea:focus {
          border-color: #2563EB !important;
          box-shadow: 0 0 0 2px rgba(37,99,235,0.16) !important;
        }

        /* Selectbox and multiselect shell */
        div[data-baseweb="select"] > div {
          border-color: rgba(148,163,184,0.7) !important;
          box-shadow: none !important;
        }

        div[data-baseweb="select"] > div:hover {
          border-color: rgba(96,165,250,0.95) !important;
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
          border-color: #2563EB !important;
          box-shadow: 0 0 0 2px rgba(37,99,235,0.16) !important;
        }

        /* Selected chips */
        [data-baseweb="tag"] {
          background: #DBEAFE !important;
          color: #1D4ED8 !important;
          border: 1px solid rgba(37,99,235,0.25) !important;
        }

        [data-baseweb="tag"] span,
        [data-baseweb="tag"] svg {
          color: #1D4ED8 !important;
          fill: #1D4ED8 !important;
        }

        /* Dropdown menu and selected items */
        div[role="listbox"] ul,
        ul[role="listbox"] {
          border: 1px solid rgba(37,99,235,0.18) !important;
          box-shadow: 0 12px 28px rgba(15,23,42,0.10) !important;
        }

        li[role="option"],
        ul[role="listbox"] li {
          color: var(--text-900) !important;
        }

        li[role="option"]:hover,
        ul[role="listbox"] li:hover {
          background: #EFF6FF !important;
        }

        li[role="option"][aria-selected="true"],
        ul[role="listbox"] li[aria-selected="true"] {
          background: #DBEAFE !important;
          color: #1D4ED8 !important;
        }

        /* Checkbox and radio */
        [data-testid="stCheckbox"] input,
        [data-testid="stRadio"] input {
          accent-color: #2563EB !important;
        }

        /* Sliders */
        [data-baseweb="slider"] [role="slider"] {
          background: #2563EB !important;
          border-color: #1D4ED8 !important;
          box-shadow: 0 0 0 2px rgba(37,99,235,0.18) !important;
        }

        [data-baseweb="slider"] > div > div > div {
          background: linear-gradient(90deg, #93C5FD 0%, #2563EB 100%) !important;
        }

        /* Number input stepper buttons */
        [data-testid="stNumberInput"] button {
          color: #2563EB !important;
        }

        /* Focus ring cleanup */
        *:focus {
          outline-color: #2563EB !important;
        }

        /* Metrics and info accents */
        [data-testid="stMetricDelta"],
        [data-testid="stMetricDelta"] svg {
          color: #2563EB !important;
          fill: #2563EB !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
