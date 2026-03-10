from typing import Dict, List
from sqlalchemy import text
from sqlalchemy.engine import Engine


class VftRepo:
    def __init__(self, engine: Engine):
        self.engine = engine

    def save_run_config(self, run_id: str, scaling_type: str = "Linear") -> None:
        """Save VFT run configuration."""
        sql = """
        INSERT INTO vft_run_config (run_id, scaling_type)
        VALUES (:run_id, :scaling_type)
        ON CONFLICT (run_id) DO UPDATE SET scaling_type = EXCLUDED.scaling_type
        """
        with self.engine.begin() as conn:
            conn.execute(text(sql), {"run_id": run_id, "scaling_type": scaling_type})

    def replace_criterion_utilities(self, run_id: str, rows: List[dict]) -> None:
        """
        Replace all criterion utilities for a run.
        Each row should have: criterion_id, weight, swing_weight, min_val, max_val
        """
        del_sql = "DELETE FROM vft_criterion_utilities WHERE run_id = :run_id"
        ins_sql = """
        INSERT INTO vft_criterion_utilities (run_id, criterion_id, weight, swing_weight, min_val, max_val)
        VALUES (:run_id, :criterion_id, :weight, :swing_weight, :min_val, :max_val)
        """
        with self.engine.begin() as conn:
            conn.execute(text(del_sql), {"run_id": run_id})
            if rows:
                conn.execute(text(ins_sql), rows)

    def replace_weighted_utilities(self, run_id: str, rows: List[dict]) -> None:
        """
        Replace all weighted utilities for a run.
        Each row should have: alternative_id, criterion_id, value
        """
        del_sql = "DELETE FROM vft_weighted_utilities WHERE run_id = :run_id"
        ins_sql = """
        INSERT INTO vft_weighted_utilities (run_id, alternative_id, criterion_id, value)
        VALUES (:run_id, :alternative_id, :criterion_id, :value)
        """
        with self.engine.begin() as conn:
            conn.execute(text(del_sql), {"run_id": run_id})
            if rows:
                conn.execute(text(ins_sql), rows)

    def replace_result_scores(self, run_id: str, rows: List[dict]) -> None:
        """
        Replace all result scores for a run.
        Each row should have: alternative_id, total_score, rank
        """
        del_sql = "DELETE FROM result_scores WHERE run_id = :run_id"
        ins_sql = """
        INSERT INTO result_scores (run_id, alternative_id, total_score, rank)
        VALUES (:run_id, :alternative_id, :total_score, :rank)
        """
        with self.engine.begin() as conn:
            conn.execute(text(del_sql), {"run_id": run_id})
            if rows:
                conn.execute(text(ins_sql), rows)
