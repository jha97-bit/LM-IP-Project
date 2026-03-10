-- VFT Standalone Schema (PostgreSQL)
-- These tables are completely independent from TOPSIS/shared MCDA schema

-- VFT Runs Table (standalone, no scenario/preference_set foreign keys)
CREATE TABLE IF NOT EXISTS vft_runs (
  run_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  executed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  executed_by TEXT,
  engine_version TEXT NOT NULL DEFAULT 'vft=0.1.0',
  note TEXT
);

-- VFT Run Configuration
CREATE TABLE IF NOT EXISTS vft_run_config (
  run_id UUID PRIMARY KEY REFERENCES vft_runs(run_id) ON DELETE CASCADE,
  scaling_type TEXT NOT NULL DEFAULT 'Linear' CHECK (scaling_type IN ('Linear', 'Custom')),
  output_min DOUBLE PRECISION NOT NULL DEFAULT 0.0,
  output_max DOUBLE PRECISION NOT NULL DEFAULT 1.0
);

-- VFT Criteria (attributes) for a run
CREATE TABLE IF NOT EXISTS vft_criteria (
  criteria_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  run_id UUID NOT NULL REFERENCES vft_runs(run_id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  weight DOUBLE PRECISION NOT NULL CHECK (weight >= 0),
  swing_weight DOUBLE PRECISION,
  min_val DOUBLE PRECISION NOT NULL,
  max_val DOUBLE PRECISION NOT NULL,
  scaling_direction TEXT NOT NULL DEFAULT 'Increasing' CHECK (scaling_direction IN ('Increasing', 'Decreasing')),
  scaling_type TEXT NOT NULL DEFAULT 'Linear' CHECK (scaling_type IN ('Linear', 'Custom')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (run_id, name)
);

CREATE INDEX IF NOT EXISTS idx_vft_criteria_run_id ON vft_criteria(run_id);

-- VFT Alternatives (options) for a run
CREATE TABLE IF NOT EXISTS vft_alternatives (
  alternative_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  run_id UUID NOT NULL REFERENCES vft_runs(run_id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (run_id, name)
);

CREATE INDEX IF NOT EXISTS idx_vft_alternatives_run_id ON vft_alternatives(run_id);

-- Raw scores (input from user)
CREATE TABLE IF NOT EXISTS vft_raw_scores (
  run_id UUID NOT NULL REFERENCES vft_runs(run_id) ON DELETE CASCADE,
  alternative_id UUID NOT NULL REFERENCES vft_alternatives(alternative_id) ON DELETE CASCADE,
  criteria_id UUID NOT NULL REFERENCES vft_criteria(criteria_id) ON DELETE CASCADE,
  value DOUBLE PRECISION NOT NULL,
  PRIMARY KEY (run_id, alternative_id, criteria_id)
);

CREATE INDEX IF NOT EXISTS idx_vft_raw_scores_run_id ON vft_raw_scores(run_id);

-- VFT Criterion Utilities (converted values per criterion)
CREATE TABLE IF NOT EXISTS vft_criterion_utilities (
  run_id UUID NOT NULL REFERENCES vft_runs(run_id) ON DELETE CASCADE,
  alternative_id UUID NOT NULL REFERENCES vft_alternatives(alternative_id) ON DELETE CASCADE,
  criteria_id UUID NOT NULL REFERENCES vft_criteria(criteria_id) ON DELETE CASCADE,
  raw_value DOUBLE PRECISION NOT NULL,
  utility_value DOUBLE PRECISION NOT NULL CHECK (utility_value >= 0 AND utility_value <= 1),
  PRIMARY KEY (run_id, alternative_id, criteria_id)
);

CREATE INDEX IF NOT EXISTS idx_vft_criterion_utilities_run_id ON vft_criterion_utilities(run_id);

-- VFT Weighted Utilities (utility × weight)
CREATE TABLE IF NOT EXISTS vft_weighted_utilities (
  run_id UUID NOT NULL REFERENCES vft_runs(run_id) ON DELETE CASCADE,
  alternative_id UUID NOT NULL REFERENCES vft_alternatives(alternative_id) ON DELETE CASCADE,
  criteria_id UUID NOT NULL REFERENCES vft_criteria(criteria_id) ON DELETE CASCADE,
  weight DOUBLE PRECISION NOT NULL,
  weighted_utility DOUBLE PRECISION NOT NULL,
  PRIMARY KEY (run_id, alternative_id, criteria_id)
);

CREATE INDEX IF NOT EXISTS idx_vft_weighted_utilities_run_id ON vft_weighted_utilities(run_id);

-- VFT Result Scores (final scores and rankings)
CREATE TABLE IF NOT EXISTS vft_result_scores (
  run_id UUID NOT NULL REFERENCES vft_runs(run_id) ON DELETE CASCADE,
  alternative_id UUID NOT NULL REFERENCES vft_alternatives(alternative_id) ON DELETE CASCADE,
  total_score DOUBLE PRECISION NOT NULL,
  rank INTEGER NOT NULL,
  PRIMARY KEY (run_id, alternative_id)
);

CREATE INDEX IF NOT EXISTS idx_vft_result_scores_run_id ON vft_result_scores(run_id);
CREATE INDEX IF NOT EXISTS idx_vft_result_scores_rank ON vft_result_scores(run_id, rank);
