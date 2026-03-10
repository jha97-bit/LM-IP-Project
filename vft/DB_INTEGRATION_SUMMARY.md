# VFT DB Integration - JSON Replaced with Database Views

## What Changed

### 1. **app.py** - Added Run History Tab & Replaced JSON
- Added import: `from src.ui.run_history import render_run_history_ui`
- Added **"Run History"** to navigation radio buttons
- **Replaced** JSON download/upload with:
  - 💾 **Database Integration** info box (auto-save enabled)
  - 📄 **JSON Export** optional backup (collapsed by default)
- JSON is now just a backup option, NOT the primary persistence
- Primary persistence is now **database** when clicking "Save & Run to Database"

### 2. **src/ui/run_history.py** (NEW FILE)
Complete new UI component to view all VFT runs and results from database with:

**Main Features:**
- 📋 **Runs Table**: Shows all VFT runs with timestamp, scenario, user, run_id
- 🔍 **Run Selector**: Click dropdown to pick a run to inspect
- 📊 **4 Detail Tabs**:
  1. **Summary**: Run metadata (dates, user, scenario IDs)
  2. **Criteria Config**: Attributes' weights, ranges, configuration
  3. **Utilities**: Computed utility values (alternatives × criteria matrix)
  4. **Scores & Rankings**: Final scores with ranks (sortable)

**Export Options:**
- Download Results as CSV
- Download Full Run as JSON (complete run data)

---

## How to See Runs in the UI

### Step 1: Create a Run (if you haven't already)
1. Go to **"Scoring & Analysis"** tab
2. Enter scores in the Scoring Matrix
3. Click **"Save & Run to Database"**
4. Note the run_id from success message

### Step 2: View in Database
1. Click on **"Run History"** in the sidebar navigation
2. You'll see a table of all VFT runs ordered by date (newest first)
3. Table shows:
   - 🕐 Executed At (date/time)
   - 📍 Scenario ID
   - ⚙️ Preference Set ID
   - 👤 Executed By
   - 🔑 Run ID

### Step 3: View Run Details
1. In **"View Run Details"** section, use the dropdown
2. Select the run you want to inspect
3. **4 tabs appear**:
   - **Summary**: Shows run metadata
   - **Criteria Config**: Shows all criteria (attributes) with weights, ranges
   - **Utilities**: Matrix of utility values for each alternative × criterion
   - **Scores & Rankings**: Final ranking with total scores

### Step 4: Export Results
- **CSV**: Click "Download Results as CSV" to get scores table
- **JSON**: Click "Download Run as JSON" to get complete run data (metadata + all tables)

---

## Data Available to View

From the database, the UI shows:

### Summary Tab
- Run ID
- Executed At (timestamp)
- Executed By (user name)
- Scenario ID
- Preference Set ID
- Scaling Type

### Criteria Config Tab
| Column | Data |
|--------|------|
| Criterion ID | UUID of attribute |
| Weight | Relative weight (0.0-1.0) |
| Swing Weight | Swing weight value |
| Min Value | Range minimum |
| Max Value | Range maximum |

### Utilities Tab
**Matrix View** (alternatives rows × criteria columns):
- Shows utility values (0.0-1.0) for each alternative-criterion combination
- Also shows raw data in expandable section

### Scores & Rankings Tab
| Column | Data |
|--------|------|
| Rank | 1, 2, 3, ... (sorted asc) |
| Alternative ID | UUID of alternative |
| Total Score | Final computed score |

Download options:
- CSV file with ranking table
- JSON with entire run data

---

## Files Modified

| File | Changes |
|------|---------|
| `app.py` | Added "Run History" nav + DB info box, hid JSON |
| `src/ui/run_history.py` | NEW: Complete run history viewer |

---

## New User Workflow

### Before (JSON-based)
1. Create model in UI
2. Click "Download Model (JSON)"
3. Later: Click "Load Model (JSON)" to restore
4. No history/audit trail
5. Hard to compare runs

### After (DB-based)
1. Create model in UI ← Same
2. Click "Save & Run to Database" ← **NEW**
3. Go to "Run History" tab ← **NEW**
4. See all previous runs ← **NEW**
5. Click to view detailed results ← **NEW**
6. Export to CSV/JSON as needed ← **NEW**
7. Full audit trail in database ← **NEW**
8. Easy to compare runs ← **NEW**

---

## Key Improvements

✅ **Persistent Storage**: Runs stay in database, not just JSON files
✅ **History**: See all previous runs, not just current model
✅ **Audit Trail**: Know who ran what, when, for which scenario
✅ **Detailed Results**: View full breakdown of utilities, scores, rankings
✅ **Export Options**: CSV for spreadsheets, JSON for archival
✅ **No Data Loss**: Older runs don't overwrit each other
✅ **Easy Comparison**: View multiple runs to compare results
✅ **Transparent**: See exactly what was stored in database

---

## Test It Now

### 1. Refresh Browser
http://localhost:8501 - You should see 6 tabs now:
- Setup
- Scaling
- Weighting
- Scoring & Analysis
- Comparison
- **Run History** ← NEW

### 2. Create a Test Run
- Go to "Scoring & Analysis" tab
- Enter scores
- Click "Save & Run to Database"
- Copy the run_id

### 3. View in Run History
- Click "Run History" tab
- You'll see your run in the table (or previous runs if they exist)
- Click dropdown to select it
- View all 4 tabs of results

### 4. Export Results
- Click "Download Results as CSV"
- Click "Download Run as JSON"

---

## Database Queries Behind the Scenes

The UI automatically runs these queries:

```sql
-- Get all VFT runs (Run History tab)
SELECT * FROM runs WHERE method = 'vft' ORDER BY executed_at DESC;

-- Get run config
SELECT * FROM vft_run_config WHERE run_id = :run_id;

-- Get criteria configuration
SELECT * FROM vft_criterion_utilities WHERE run_id = :run_id;

-- Get computed utilities
SELECT * FROM vft_weighted_utilities WHERE run_id = :run_id;

-- Get final scores & rankings
SELECT * FROM result_scores WHERE run_id = :run_id ORDER BY rank;
```

All automatic - no SQL needed from user!

---

## What About JSON?

JSON is now **optional backup only**:
- Collapsed in sidebar by default
- Label changed to "📄 JSON Export (Optional Backup)"
- Primary persistence is **DATABASE**
- JSON can still be used for:
  - Exporting current model for sharing
  - Loading a saved model locally
  - Offline backup

---

## Summary

| Feature | Before | After |
|---------|--------|-------|
| Persistence | JSON file | Database ✓ |
| History | None | Full run history ✓ |
| View Results | No | Run History tab ✓ |
| Export | JSON only | CSV + JSON ✓ |
| Audit Trail | No | Full audit ✓ |
| Multiple Runs | Overwrite | All saved ✓ |

**The VFT app is now fully database-driven!**
