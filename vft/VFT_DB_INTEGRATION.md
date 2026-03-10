# VFT Database Integration - Implementation Summary

## What Changed

### 1. **UI Integration** ([src/ui/analysis.py](src/ui/analysis.py))
Added a "Save & Run to Database" section in the **Scoring & Analysis** tab with:
- Input fields: `scenario_id`, `preference_set_id`, `executed_by`
- Button: **"Save & Run to Database"** (type="primary")
- Automatic SQL verification queries display

### 2. **Service Export** ([services/__init__.py](services/__init__.py))
Added `__all__ = ["VftService"]` to enable proper imports.

### 3. **No Changes Required**
These already existed and are now wired:
- ✅ `persistence/engine.py` - Database connection
- ✅ `persistence/repositories/run_repo.py` - Run table writes
- ✅ `persistence/repositories/vft_repo.py` - VFT-specific writes

---

## How to Use

### Step 1: Run the Streamlit App
```bash
cd /Users/ritikaloganayagi/Desktop/Industry\ Prac/vft
streamlit run app.py
```

### Step 2: Navigate to "Scoring & Analysis" Tab
1. Create attributes in **Setup** tab
2. Create alternatives in **Setup** tab
3. Enter raw scores in **Scoring Matrix** (tab 1)
4. Go to **Analysis Dashboard** (tab 2)

### Step 3: Save to Database
In the **"Save Run to Database"** section:
1. Enter `scenario_id` (UUID or use default)
2. Enter `preference_set_id` (UUID or use default)
3. Optionally enter `executed_by` name
4. Click **"Save & Run to Database"** button

### Step 4: See the Run ID
A success message shows: `✓ VFT run saved with ID: <run_id>`

### Step 5: Verify with SQL (expand section in UI)
Click "Verification SQL Queries" to see copyable queries for psql.

---

## Exact SQL Queries to Verify

After clicking "Save & Run to Database", run these in `psql`:

```sql
-- Replace <run_id> with the UUID shown in the UI

-- 1. Verify run was created
SELECT * FROM runs WHERE run_id = '<run_id>'::uuid AND method = 'vft';

-- 2. Verify run configuration
SELECT * FROM vft_run_config WHERE run_id = '<run_id>'::uuid;

-- 3. Verify criterion utilities (attributes/criteria saved)
SELECT 
  criterion_id,
  weight,
  swing_weight,
  min_val,
  max_val
FROM vft_criterion_utilities 
WHERE run_id = '<run_id>'::uuid;

-- 4. Verify weighted utilities (utility values for each alternative x criterion)
SELECT 
  alternative_id,
  criterion_id,
  value AS weighted_utility
FROM vft_weighted_utilities
WHERE run_id = '<run_id>'::uuid;

-- 5. Verify result scores (final scores and rankings)
SELECT 
  alternative_id,
  total_score,
  rank
FROM result_scores
WHERE run_id = '<run_id>'::uuid
ORDER BY rank ASC;

-- 6. Count summary
SELECT 
  (SELECT COUNT(*) FROM vft_criterion_utilities WHERE run_id = '<run_id>'::uuid) as criteria_count,
  (SELECT COUNT(*) FROM vft_weighted_utilities WHERE run_id = '<run_id>'::uuid) as utility_values_count,
  (SELECT COUNT(*) FROM result_scores WHERE run_id = '<run_id>'::uuid) as alternatives_count;
```

---

## Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│ Streamlit UI: Scoring & Analysis Tab                        │
│ - Score matrix (raw values)                                 │
│ - "Save & Run to Database" button                           │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ services.VftService.execute_vft_run()                       │
│ - Receives model with attributes, alternatives, scores     │
│ - Computes utilities (attr.get_value(raw_score))           │
│ - Computes weighted utilities (utility * weight)           │
│ - Calculates total scores & ranks                          │
└──────────────────────┬──────────────────────────────────────┘
                       │
       ┌───────────────┼───────────────┬──────────────────┐
       │               │               │                  │
       ▼               ▼               ▼                  ▼
   ┌────────────┐ ┌────────────┐ ┌──────────────┐ ┌────────────┐
   │ RunRepo    │ │ VftRepo    │ │ VftRepo      │ │ VftRepo    │
   │ .create    │ │ .save_conf │ │ .replace_crit│ │ .replace_ws│
   │ _run()     │ │ ig()       │ │ _utilities() │ │ eighted()  │
   └───┬────────┘ └────────────┘ └──────────────┘ └────────────┘
       │               │               │                  │
       └───────────────┼───────────────┴──────────────────┘
                       │
       ┌───────────────┼───────────────┐
       │               │               │
       ▼               ▼               ▼
  ┌─────────┐    ┌──────────────┐   ┌────────────┐
  │ runs    │    │ vft_run_cfg  │   │ vft_crit_u │
  │ (insert)│    │ (upsert)     │   │ tilities   │
  └─────────┘    └──────────────┘   │ (replace)  │
                                     └────────────┘
                                     
                                     ┌──────────────┐
                                     │ vft_weighted │
                                     │ _utilities   │
                                     │ (replace)    │
                                     └──────────────┘
                                     
                                     ┌──────────────┐
                                     │ result_scores│
                                     │ (replace)    │
                                     └──────────────┘
```

---

## Code Reference

### When Button Clicked
```python
# File: src/ui/analysis.py (lines 55-100)
if st.button("Save & Run to Database", type="primary", key="save_to_db"):
    engine = get_engine()
    vft_service = VftService(engine)
    run_id = vft_service.execute_vft_run(
        scenario_id=scenario_id,
        preference_set_id=preference_set_id,
        model=model,
        scaling_type="Linear",
        executed_by=executed_by or "vft_ui"
    )
```

### Service Execution
```python
# File: services/__init__.py (lines 24-90)
def execute_vft_run(...) -> str:
    run_id = self.run_repo.create_run(...)  # INSERT into runs
    self.vft_repo.save_run_config(...)      # UPSERT vft_run_config
    self.vft_repo.replace_criterion_utilities(...)  # DELETE + INSERT
    self.vft_repo.replace_weighted_utilities(...)   # DELETE + INSERT
    self.vft_repo.replace_result_scores(...)        # DELETE + INSERT
    return run_id
```

### Repository Pattern
```python
# File: persistence/repositories/vft_repo.py

class VftRepo:
    def save_run_config(run_id, scaling_type):
        # ON CONFLICT (run_id) DO UPDATE SET ...
        
    def replace_criterion_utilities(run_id, rows):
        # DELETE WHERE run_id = :run_id
        # INSERT ... VALUES (...)
        
    def replace_weighted_utilities(run_id, rows):
        # DELETE WHERE run_id = :run_id
        # INSERT ... VALUES (...)
        
    def replace_result_scores(run_id, rows):
        # DELETE WHERE run_id = :run_id
        # INSERT ... VALUES (...)
```

---

## Verify Installation

Run the verification script:
```bash
cd /Users/ritikaloganayagi/Desktop/Industry\ Prac/vft
python3 verify_vft_db.py
```

This will show:
- Latest VFT run ID
- Count of rows in each table
- Sample data from vft_run_config and vft_criterion_utilities

---

## What Gets Persisted

| Table | What | Source |
|-------|------|--------|
| `runs` | Metadata: scenario_id, preference_set_id, method='vft', executed_by, timestamp | VftService.execute_vft_run() |
| `vft_run_config` | Scaling type, output range, missing policy | VftService (scaling_type param) |
| `vft_criterion_utilities` | Criterion ID, weight, swing_weight, min/max for each attribute | model.attributes |
| `vft_weighted_utilities` | Alternative ID, criterion ID, utility value for each (alt, criterion) | attr.get_value() × attr.weight |
| `result_scores` | Alternative ID, total score, rank for each alternative | model.calculate_scores() sorted descending |

---

## Idempotency

All writes use "replace" semantics:
- **vft_run_config**: UPSERT (replace on conflict)
- **vft_criterion_utilities**: DELETE then INSERT
- **vft_weighted_utilities**: DELETE then INSERT
- **result_scores**: DELETE then INSERT

This means **clicking "Save & Run" twice with the same run_id will overwrite** (idempotent).

---

## Schema Requirements (Verified)

These tables must already exist in PostgreSQL:
```sql
CREATE TABLE runs (
    run_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scenario_id UUID NOT NULL,
    preference_set_id UUID NOT NULL,
    method VARCHAR(50) NOT NULL,  -- 'vft' or 'topsis'
    engine_version VARCHAR(100),
    executed_by VARCHAR(100) DEFAULT '',
    executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE vft_run_config (
    run_id UUID PRIMARY KEY REFERENCES runs(run_id),
    scaling_type VARCHAR(50) DEFAULT 'Linear'
);

CREATE TABLE vft_criterion_utilities (
    run_id UUID REFERENCES runs(run_id),
    criterion_id UUID,
    weight FLOAT NOT NULL,
    swing_weight FLOAT NOT NULL,
    min_val FLOAT NOT NULL,
    max_val FLOAT NOT NULL,
    PRIMARY KEY (run_id, criterion_id)
);

CREATE TABLE vft_weighted_utilities (
    run_id UUID REFERENCES runs(run_id),
    alternative_id UUID,
    criterion_id UUID,
    value FLOAT NOT NULL,
    PRIMARY KEY (run_id, alternative_id, criterion_id)
);

CREATE TABLE result_scores (
    run_id UUID REFERENCES runs(run_id),
    alternative_id UUID,
    total_score FLOAT NOT NULL,
    rank INTEGER NOT NULL,
    PRIMARY KEY (run_id, alternative_id)
);
```
