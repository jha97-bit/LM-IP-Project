"""
WALKTHROUGH: What Happens When You Click "Save & Run to Database"

This file shows the exact execution flow with line numbers and code references.
"""

# ==============================================================================
# STEP 1: User Interaction (UI Layer)
# ==============================================================================
# File: src/ui/analysis.py, lines 88-100
# 
# Code:
#   if st.button("Save & Run to Database", type="primary", key="save_to_db"):
#       if not model.attributes:
#           st.error("No attributes...")
#       elif not model.alternatives:
#           st.error("No alternatives...")
#       else:
#           try:
#               engine = get_engine()  # ← Load DB connection from .env
#               vft_service = VftService(engine)  # ← Create service
#               run_id = vft_service.execute_vft_run(
#                   scenario_id=scenario_id,  # ← User-provided UUID
#                   preference_set_id=preference_set_id,  # ← User-provided UUID
#                   model=model,  # ← Current VFTModel in session_state
#                   scaling_type="Linear",
#                   executed_by=executed_by or "vft_ui"  # ← Optional user name
#               )
#               st.success(f"✓ VFT run saved with ID: {run_id}")

# ==============================================================================
# STEP 2: Service Orchestration
# ==============================================================================
# File: services/__init__.py, lines 24-90
#
# Method: VftService.execute_vft_run()
# Transaction: with engine.begin() as conn:

STEP_2_PSEUDOCODE = """
def execute_vft_run(scenario_id, preference_set_id, model, ...):
    
    # 2.1: Create run record (gets back run_id UUID)
    run_id = RunRepo(engine).create_run(
        scenario_id=scenario_id,
        preference_set_id=preference_set_id,
        method="vft",  # ← Important: marks this as VFT method
        executed_by=executed_by,
        engine_version="core=0.1.0"
    )
    # ↓ INSERT INTO runs (scenario_id, preference_set_id, method, ...)
    #   VALUES (...) RETURNING run_id
    
    # 2.2: Save run configuration
    VftRepo(engine).save_run_config(run_id, scaling_type="Linear")
    # ↓ INSERT INTO vft_run_config (run_id, scaling_type)
    #   VALUES (:run_id, :scaling_type)
    #   ON CONFLICT (run_id) DO UPDATE SET scaling_type = EXCLUDED.scaling_type
    
    # 2.3: Extract and save criterion data
    criterion_utilities = []
    for attr in model.attributes:  # ← Loop over attributes from UI
        criterion_utilities.append({
            "run_id": run_id,
            "criterion_id": attr.id,  # ← UUID
            "weight": attr.weight,  # ← From weighting UI slider
            "swing_weight": attr.swing_weight,  # ← From weighting UI
            "min_val": attr.min_val,  # ← From setup UI
            "max_val": attr.max_val   # ← From setup UI
        })
    VftRepo(engine).replace_criterion_utilities(run_id, criterion_utilities)
    # ↓ DELETE FROM vft_criterion_utilities WHERE run_id = :run_id
    # ↓ INSERT INTO vft_criterion_utilities (...) VALUES (...)
    
    # 2.4: Compute and save weighted utilities
    weighted_utilities = []
    for alt in model.alternatives:  # ← Loop over alternatives
        for attr in model.attributes:  # ← Loop over attributes
            raw_score = alt.get_score(attr.name)  # ← From scoring matrix
            value = attr.get_value(raw_score)  # ← Compute utility via scaling
            # value is 0.0-1.0 based on:
            #   - Linear: (raw_score - min) / (max - min)
            #   - Custom: interpolation of custom points
            weighted_utilities.append({
                "run_id": run_id,
                "alternative_id": alt.id,  # ← UUID
                "criterion_id": attr.id,   # ← UUID
                "value": value  # ← Float 0.0-1.0
            })
    VftRepo(engine).replace_weighted_utilities(run_id, weighted_utilities)
    # ↓ DELETE FROM vft_weighted_utilities WHERE run_id = :run_id
    # ↓ INSERT INTO vft_weighted_utilities (...) VALUES (...)
    
    # 2.5: Calculate and save result scores
    df_scores = model.calculate_scores()  # ← Query: model.calculate_scores()
    #   Returns DataFrame with:
    #   - Column "Alternative": name of alternative
    #   - Columns "{attr.name} (Weighted)": utility * weight
    #   - Column "Total Score": sum of weighted utilities
    
    result_scores = []
    df_sorted = df_scores.sort_values("Total Score", ascending=False)
    
    for rank, row in df_sorted.iterrows():
        alt_name = row["Alternative"]
        total_score = row["Total Score"]
        
        alt = next((a for a in model.alternatives if a.name == alt_name), None)
        if alt:
            result_scores.append({
                "run_id": run_id,
                "alternative_id": alt.id,  # ← UUID
                "total_score": total_score,  # ← Float (sum of weighted utilities)
                "rank": rank + 1  # ← 1-indexed rank
            })
    VftRepo(engine).replace_result_scores(run_id, result_scores)
    # ↓ DELETE FROM result_scores WHERE run_id = :run_id
    # ↓ INSERT INTO result_scores (...) VALUES (...)
    
    return run_id  # ← Back to UI
"""

# ==============================================================================
# STEP 3: Repository Layer Execution
# ==============================================================================
# File: persistence/repositories/run_repo.py, lines 11-26
#
# RunRepo.create_run:

RUN_REPO_CODE = """
def create_run(self, scenario_id, preference_set_id, method, executed_by, engine_version):
    sql = '''
    INSERT INTO runs (scenario_id, preference_set_id, method, engine_version, executed_by)
    VALUES (:scenario_id, :preference_set_id, :method, :engine_version, :executed_by)
    RETURNING run_id::text AS run_id
    '''
    with self.engine.begin() as conn:  # ← Transaction begins here
        row = conn.execute(
            text(sql),
            {
                "scenario_id": scenario_id,
                "preference_set_id": preference_set_id,
                "method": method,  # ← 'vft'
                "engine_version": engine_version,
                "executed_by": executed_by,
            },
        ).mappings().first()
    return str(row["run_id"])  # ← Get UUID from DB
"""

# ==============================================================================
# STEP 4: Database Tables Updated
# ==============================================================================

TABLES_UPDATED = """
Table: runs
  INSERT VALUES (
    scenario_id: <uuid from UI>,
    preference_set_id: <uuid from UI>,
    method: 'vft',
    executed_by: <name from UI>,
    engine_version: 'core=0.1.0',
    executed_at: now()  -- auto
  )
  RETURNS run_id: <new uuid>

Table: vft_run_config
  INSERT/UPDATE VALUES (
    run_id: <from above>,
    scaling_type: 'Linear'
  )

Table: vft_criterion_utilities
  DELETE WHERE run_id = <run_id>
  INSERT VALUES (
    run_id: <run_id>,
    criterion_id: <attr.id>,
    weight: <attr.weight>,
    swing_weight: <attr.swing_weight>,
    min_val: <attr.min_val>,
    max_val: <attr.max_val>
  ) × N attributes

Table: vft_weighted_utilities
  DELETE WHERE run_id = <run_id>
  INSERT VALUES (
    run_id: <run_id>,
    alternative_id: <alt.id>,
    criterion_id: <attr.id>,
    value: <utility 0.0-1.0>
  ) × N alternatives × N criteria

Table: result_scores
  DELETE WHERE run_id = <run_id>
  INSERT VALUES (
    run_id: <run_id>,
    alternative_id: <alt.id>,
    total_score: <sum of weighted utilities>,
    rank: <1, 2, 3, ...>
  ) × N alternatives
"""

# ==============================================================================
# STEP 5: UI Response
# ==============================================================================
UI_RESPONSE = """
User sees:
  ✓ VFT run saved with ID: 550e8400-e29b-41d4-a716-446655440000
  
  Verification SQL Queries
  [Click to expand]
  
  SELECT * FROM runs WHERE run_id = '550e8400-e29b-41d4-a716-446655440000'::uuid;
  SELECT * FROM vft_run_config WHERE run_id = '550e8400-e29b-41d4-a716-446655440000'::uuid;
  SELECT * FROM vft_criterion_utilities WHERE run_id = '550e8400-e29b-41d4-a716-446655440000'::uuid;
  SELECT * FROM vft_weighted_utilities WHERE run_id = '550e8400-e29b-41d4-a716-446655440000'::uuid;
  SELECT * FROM result_scores WHERE run_id = '550e8400-e29b-41d4-a716-446655440000'::uuid;
"""

# ==============================================================================
# DATA FLOW DIAGRAM
# ==============================================================================

DIAGRAM = """
┌─────────────────────────────────────────────────────────────────────────┐
│ USER CLICKS: "Save & Run to Database"                                   │
│ Location: Scoring & Analysis Tab                                        │
│ File: src/ui/analysis.py:88                                             │
└──────────────────────────┬──────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ INPUTS:                                                                  │
│  - scenario_id: UUID (from text_input)                                  │
│  - preference_set_id: UUID (from text_input)                            │
│  - executed_by: str (optional, from text_input)                         │
│  - model: VFTModel (from st.session_state)                              │
│    ├─ model.attributes: List[Attribute]                                 │
│    │  └─ Each has: id, name, weight, swing_weight, min_val, max_val    │
│    └─ model.alternatives: List[Alternative]                             │
│       └─ Each has: id, name, scores: {attr.name: raw_score}            │
└──────────────────────────┬──────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ STEP 1: VftService.execute_vft_run()                                    │
│ File: services/__init__.py:24-90                                        │
│                                                                          │
│ with engine.begin() as conn:  ← TRANSACTION START                      │
│   run_id ← RunRepo.create_run()  ← Inserts runs record                 │
│         ← VftRepo.save_run_config()  ← Inserts/updates config          │
│         ← VftRepo.replace_criterion_utilities()  ← Saves criteria      │
│         ← VftRepo.replace_weighted_utilities()   ← Saves utilities     │
│         ← VftRepo.replace_result_scores()        ← Saves final scores  │
│                                      ← TRANSACTION COMMIT (or rollback) │
└──────────────────────────┬──────────────────────────────────────────────┘
                           │
           ┌───────────────┼───────────────┬───────────────┬────────────┐
           │               │               │               │            │
           ▼               ▼               ▼               ▼            ▼
    ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
    │ INSERT runs  │ │ UPSERT vft_  │ │ DELETE then  │ │ DELETE then  │ │ DELETE then  │
    │              │ │ run_config   │ │ INSERT vft_  │ │ INSERT vft_  │ │ INSERT result│
    │ ↓            │ │              │ │ criterion_   │ │ weighted_    │ │ _scores      │
    │ Runs table   │ │ ↓            │ │ utilities    │ │ utilities    │ │              │
    │              │ │ vft_run_cfg  │ │              │ │              │ │ ↓            │
    │ run_id (PK)  │ │              │ │ ↓            │ │ ↓            │ │ result_scores│
    │ scenario_id  │ │ run_id (PK)  │ │ vft_criterion│ │ vft_weighted │ │              │
    │ pref_set_id  │ │ scaling_type │ │ _utilities   │ │ _utilities   │ │ (alternative,│
    │ method=vft   │ │              │ │              │ │              │ │  score,      │
    │ executed_by  │ │              │ │ criterion_id │ │ alternative_ │ │  rank)       │
    │ timestamp    │ │              │ │ weight       │ │ id           │ │              │
    └──────────────┘ └──────────────┘ │ swing_weight │ │ criterion_id │ └──────────────┘
                                       │ min/max_val  │ │ value        │
                                       └──────────────┘ └──────────────┘
                                                  │
                                                  ▼
                                       All in DB transaction
                                       ✓ On success: COMMIT
                                       ✗ On error: ROLLBACK
                                                  │
           ┌─────────────────────────────────────┴────────────────────┐
           │                                                          │
           ▼                                                          ▼
    Success in UI                              Error in UI
    st.success(f"✓ VFT run saved...")         st.error(f"Failed...")
    Show SQL verification queries              User can retry
"""

print(DIAGRAM)
print("\n" + "="*80)
print("DETAILED CODE FLOW")
print("="*80)
print(STEP_2_PSEUDOCODE)
print("\n" + "="*80)
print("REPOSITORY EXECUTION")
print("="*80)
print(RUN_REPO_CODE)
print("\n" + "="*80)
print("TABLES UPDATED")
print("="*80)
print(TABLES_UPDATED)
print("\n" + "="*80)
print("UI RESPONSE")
print("="*80)
print(UI_RESPONSE)
