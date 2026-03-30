# Integrated MCDA Tool — TOPSIS + VFT + AHP (reserved)

A Streamlit application for Multi-Criteria Decision Analysis (MCDA) with a **unified Run Model** step:
- **TOPSIS** — Technique for Order of Preference by Similarity to Ideal Solution
- **VFT** — Value-Focused Thinking with user-defined value functions
- **AHP** — Analytic Hierarchy Process (scenario type + schema support; pairwise engine not implemented yet)

---

## Setup

### 1. Prerequisites

- Python 3.10+
- PostgreSQL 14+

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment

```bash
cp .env.example .env
# Edit .env and set DATABASE_URL
```

### 4. Create the database schema

```bash
psql -d mcda_db -f schema/schema.sql
# If upgrading an existing DB, also apply:
# psql -d mcda_db -f schema/migrations/20260330_add_ahp_method.sql
```

### 5. Run the app

```bash
cd app
streamlit run streamlit_app.py
```

---

## Page Flow

| Step | Page | Description |
|------|------|-------------|
| Home | `streamlit_app.py` | Overview and live DB stats |
| 1 | `1_decision_setup.py` | Create/select Decision & Scenario; import `.mcda` files |
| 2 | `2_data_input.py` | Add alternatives, criteria, measurement matrix, preference sets |
| 3 | `3_preferences.py` | Legacy router (redirects to Run Model or Value Functions) |
| 3 | `3_run_models.py` | **Unified run step** — TOPSIS, VFT, or AHP placeholder |
| 3a | `3a_run_topsis.py` | Redirect → `3_run_models.py` |
| 3b | `3b_vft_value_functions.py` | Define VFT value functions per criterion |
| 3c | `3c_run_vft.py` | Redirect → `3_run_models.py` |
| 4 | `4_results.py` | View rankings, charts, and run notes |
| 5 | `5_sensitivity.py` | Sensitivity analysis and preference set comparison |
| 6 | `6_report_builder.py` | Build and download a DOCX report |
| 7 | `7_history.py` | Run history, export `.mcda`, danger zone |

---

## Scenario Sharing

Export any scenario as a `.mcda` file from **Step 7 → Export Scenario**.

A colleague can import it on **Step 1 → Import .mcda** to recreate the full scenario (alternatives, criteria, weights, value functions, and all run results) in their own database instance.

---

## Project Structure

```
mcda_tool/
├── app/
│   ├── bootstrap.py          # Adds project root to sys.path
│   ├── streamlit_app.py      # Home page
│   └── pages/                # Numbered step pages
├── core/
│   ├── topsis.py             # TOPSIS computation engine
│   ├── vft_model.py          # VFT model + Attribute classes
│   ├── normalization.py
│   ├── distance.py
│   └── validation.py
├── persistence/
│   ├── engine.py             # SQLAlchemy engine (reads DATABASE_URL)
│   └── repositories/         # DB access layer per entity
├── services/
│   ├── scenario_service.py   # Scenario CRUD helpers
│   ├── topsis_service.py     # TOPSIS run + persist
│   ├── vft_service.py        # VFT run + persist
│   ├── scenario_share_service.py  # .mcda export / import
│   ├── delete_service.py     # Cascading deletes
│   └── audit_service.py      # Audit log helpers
└── schema/
    └── schema.sql            # Full DB schema (TOPSIS + VFT tables)
```
