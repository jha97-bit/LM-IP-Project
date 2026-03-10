#!/usr/bin/env python3
"""
QUICK VISUAL GUIDE - What You Should See in the UI
"""

SIDEBAR_BEFORE = """
BEFORE (JSON only):
┌─ Sidebar ────────────────────┐
│ Navigation                   │
│  • Setup                     │
│  • Scaling                   │
│  • Weighting                 │
│  • Scoring & Analysis        │
│  • Comparison                │
│                              │
│ ─────────────────────────    │
│ Model Management             │
│                              │
│ [📥 Download Model (JSON)] │
│ [□ Load Model (JSON)]      │
│                              │
└──────────────────────────────┘
"""

SIDEBAR_AFTER = """
AFTER (Database primary, JSON optional):
┌─ Sidebar ────────────────────┐
│ Navigation                   │
│  • Setup                     │
│  • Scaling                   │
│  • Weighting                 │
│  • Scoring & Analysis        │
│  • Comparison                │
│  • Run History        ← NEW! │
│                              │
│ ─────────────────────────    │
│ Model Management             │
│                              │
│ ▼ 💾 Database Integration    │
│   Active: Runs saved to DB   │
│   Go to Run History tab...   │
│                              │
│ ▼ 📄 JSON Export (Backup)    │
│   [📥 Download Model]        │
│   [□ Load Model]             │
│                              │
└──────────────────────────────┘
"""

RUN_HISTORY_TAB = """
RUN HISTORY TAB (New page):
┌─────────────────────────────────────────────────┐
│ Run History & Results                           │
│                                                 │
│ ┌─ VFT Runs Table ──────────────────────────┐  │
│ │ Executed At      │ Scenario ID │ User  │  │  │
│ ├──────────────────┼─────────────┼───────┤  │  │
│ │ 2026-03-09 14:32 │ 550e8400... │ test  │  │  │
│ │ 2026-03-09 14:15 │ 550e8400... │ admin │  │  │
│ │ 2026-03-09 13:45 │ 110e8400... │ test  │  │  │
│ └──────────────────┴─────────────┴───────┘  │  │
│                                                 │
│ ─────────────────────────────────────────────   │
│ View Run Details                                │
│                                                 │
│ Select a run: [dropdown ▼]                     │
│   └─ 2026-03-09 14:32 - test - 550e8400...    │
│                                                 │
│ ┌─ [Summary│Criteria Config│Utilities│Scores] │
│ │                                             │
│ │ Run Information                             │
│ │                                             │
│ │ Run ID: 550e8400-e29b-41d4-a716-44665... │
│ │ Executed At: 2026-03-09 14:32:15          │
│ │ Executed By: test_user                    │
│ │ Scenario ID: 550e8400-e29b-41d4...        │
│ │ Preference Set ID: 550e8400-e29b-41...    │
│ │ Scaling Type: Linear                      │
│ │                                             │
│ └─ [🔽 Download Results as CSV]              │
│    [🔽 Download Run as JSON]                  │
│                                                 │
└─────────────────────────────────────────────────┘
"""

CRITERIA_CONFIG_TAB = """
CRITERIA CONFIG TAB:
┌──────────────┬─────────┬──────────────┬─────────┬─────────┐
│ Criterion ID │ Weight  │ Swing Weight │ Min Val │ Max Val │
├──────────────┼─────────┼──────────────┼─────────┼─────────┤
│ 550e8400-... │ 0.333   │ 50.0         │ 0.0     │ 100.0   │
│ 660e8400-... │ 0.333   │ 50.0         │ 0.0     │ 10.0    │
│ 770e8400-... │ 0.334   │ 50.0         │ 0.0     │ 50.0    │
└──────────────┴─────────┴──────────────┴─────────┴─────────┘
"""

UTILITIES_TAB = """
UTILITIES TAB (Alternatives × Criteria Matrix):
┌──────────────┬──────────────┬──────────────┬──────────────┐
│ Alternative  │ Criterion 1  │ Criterion 2  │ Criterion 3  │
├──────────────┼──────────────┼──────────────┼──────────────┤
│ 550e8400-... │ 0.500        │ 0.800        │ 0.400        │
│ 660e8400-... │ 0.250        │ 0.900        │ 0.600        │
│ 770e8400-... │ 0.750        │ 0.600        │ 0.450        │
└──────────────┴──────────────┴──────────────┴──────────────┘
"""

SCORES_TAB = """
SCORES & RANKINGS TAB:
┌──────┬──────────────┬─────────────┐
│ Rank │ Alternative  │ Total Score │
├──────┼──────────────┼─────────────┤
│ 1    │ 770e8400-... │ 0.5280      │
│ 2    │ 550e8400-... │ 0.5600      │
│ 3    │ 660e8400-... │ 0.4200      │
└──────┴──────────────┴─────────────┘

[🔽 Download Results as CSV]
[🔽 Download Run as JSON]
"""

WORKFLOW = """
FULL WORKFLOW - Step by Step
════════════════════════════════════════════════════════════

1. CREATE MODEL
   └─ Go to "Setup" tab
   └─ Add attributes (Cost, Quality, Speed)
   └─ Add alternatives (Option A, B, C)

2. CONFIGURE
   └─ Go to "Scaling" tab (optional)
   └─ Adjust scaling if needed

3. SET WEIGHTS
   └─ Go to "Weighting" tab
   └─ Use sliders to set weights

4. SCORE & SAVE ⭐ KEY STEP
   └─ Go to "Scoring & Analysis" tab
   └─ Enter raw scores in "Scoring Matrix" editor
   └─ Scroll down to "Save Run to Database" section
   └─ Click [Save & Run to Database] button ← This triggers persistence!
   └─ See success: "✓ VFT run saved with ID: <uuid>"
   └─ Copy the run_id

5. VIEW RESULTS
   └─ Click "Run History" tab in sidebar ← NEW!
   └─ See table of all VFT runs
   └─ Choose run from dropdown
   └─ View 4 tabs: Summary, Criteria, Utilities, Scores
   └─ Download CSV or JSON

6. COMPARE (Optional)
   └─ Select another run from dropdown
   └─ See its results
   └─ Compare different scenario results

════════════════════════════════════════════════════════════
"""

WHAT_CHANGED = """
WHAT'S DIFFERENT FROM JSON VERSION
═══════════════════════════════════════════════════════════

JSON VERSION:
✗ Download model as JSON file
✗ Load JSON file back
✗ No history
✗ No way to see past runs
✗ Data only in your files

DATABASE VERSION (NOW):
✓ Automatically saved to PostgreSQL
✓ View all previous runs in "Run History" tab
✓ See detailed breakdown: criteria, utilities, scores
✓ Export each run as CSV or JSON
✓ Full audit trail (who, when, what scenario)
✓ Team can share runs (all in shared database)
✓ Easy to compare different scenarios

═══════════════════════════════════════════════════════════
"""

print(SIDEBAR_BEFORE)
print("\n" + "="*70 + "\n")
print(SIDEBAR_AFTER)
print("\n" + "="*70 + "\n")
print(RUN_HISTORY_TAB)
print("\n" + "="*70 + "\n")
print(CRITERIA_CONFIG_TAB)
print("\n" + "="*70 + "\n")
print(UTILITIES_TAB)
print("\n" + "="*70 + "\n")
print(SCORES_TAB)
print("\n" + "="*70 + "\n")
print(WORKFLOW)
print("\n" + "="*70 + "\n")
print(WHAT_CHANGED)
