"""
VFT Standalone Data Repository
Persists criteria, alternatives, utilities, and results
"""
from typing import List, Dict, Any
from sqlalchemy import text
from sqlalchemy.engine import Engine


class VftDataRepo:
    """Repository for VFT data persistence (criteria, alternatives, utilities, scores)."""
    
    def __init__(self, engine: Engine):
        self.engine = engine
    
    # ==================== Run Configuration ====================
    
    def save_run_config(
        self,
        run_id: str,
        scaling_type: str = "Linear",
        output_min: float = 0.0,
        output_max: float = 1.0,
    ) -> None:
        """Save or update VFT run configuration."""
        sql = """
        INSERT INTO vft_run_config (run_id, scaling_type, output_min, output_max)
        VALUES (:run_id, :scaling_type, :output_min, :output_max)
        ON CONFLICT (run_id) DO UPDATE SET 
            scaling_type = EXCLUDED.scaling_type,
            output_min = EXCLUDED.output_min,
            output_max = EXCLUDED.output_max
        """
        with self.engine.begin() as conn:
            conn.execute(
                text(sql),
                {
                    "run_id": run_id,
                    "scaling_type": scaling_type,
                    "output_min": output_min,
                    "output_max": output_max,
                },
            )
    
    # ==================== Criteria (Attributes) ====================
    
    def replace_criteria(self, run_id: str, criteria_list: List[Dict[str, Any]]) -> List[str]:
        """
        Replace all criteria for a run.
        
        Each criteria dict should have:
        - criteria_id: str (UUID, optional - will be generated if not provided)
        - name: str
        - weight: float
        - swing_weight: float (optional)
        - min_val: float
        - max_val: float
        - scaling_direction: str ('Increasing' or 'Decreasing')
        - scaling_type: str ('Linear' or 'Custom')
        
        Returns: List of criteria_ids in the same order as input
        """
        # Delete existing
        del_sql = "DELETE FROM vft_criteria WHERE run_id = CAST(:run_id AS UUID)"
        
        # Insert new with RETURNING to get back the IDs
        ins_sql = """
        INSERT INTO vft_criteria 
        (run_id, criteria_id, name, weight, swing_weight, min_val, max_val, scaling_direction, scaling_type)
        VALUES 
        (:run_id, COALESCE(:criteria_id, gen_random_uuid()), :name, :weight, :swing_weight, :min_val, :max_val, :scaling_direction, :scaling_type)
        RETURNING criteria_id::text AS criteria_id
        """
        
        with self.engine.begin() as conn:
            conn.execute(text(del_sql), {"run_id": run_id})
            criteria_ids = []
            if criteria_list:
                for c in criteria_list:
                    row = {"run_id": run_id, **c}
                    result = conn.execute(text(ins_sql), row).mappings().first()
                    criteria_ids.append(str(result["criteria_id"]))
            return criteria_ids
    
    # ==================== Alternatives ====================
    
    def replace_alternatives(self, run_id: str, alternatives: List[Dict[str, Any]]) -> List[str]:
        """
        Replace all alternatives for a run.
        
        Each alternative dict should have:
        - alternative_id: str (UUID, optional - will be generated if not provided)
        - name: str
        
        Returns: List of alternative_ids in the same order as input
        """
        del_sql = "DELETE FROM vft_alternatives WHERE run_id = CAST(:run_id AS UUID)"
        ins_sql = """
        INSERT INTO vft_alternatives (run_id, alternative_id, name)
        VALUES (:run_id, COALESCE(:alternative_id, gen_random_uuid()), :name)
        RETURNING alternative_id::text AS alternative_id
        """
        
        with self.engine.begin() as conn:
            conn.execute(text(del_sql), {"run_id": run_id})
            alt_ids = []
            if alternatives:
                for a in alternatives:
                    row = {"run_id": run_id, **a}
                    result = conn.execute(text(ins_sql), row).mappings().first()
                    alt_ids.append(str(result["alternative_id"]))
            return alt_ids
    
    # ==================== Raw Scores ====================
    
    def replace_raw_scores(self, run_id: str, scores: List[Dict[str, Any]]) -> None:
        """
        Replace all raw scores for a run.
        
        Each score dict should have:
        - alternative_id: str (UUID)
        - criteria_id: str (UUID)
        - value: float
        """
        del_sql = "DELETE FROM vft_raw_scores WHERE run_id = CAST(:run_id AS UUID)"
        ins_sql = """
        INSERT INTO vft_raw_scores (run_id, alternative_id, criteria_id, value)
        VALUES (:run_id, :alternative_id, :criteria_id, :value)
        """
        
        with self.engine.begin() as conn:
            conn.execute(text(del_sql), {"run_id": run_id})
            if scores:
                rows = [{"run_id": run_id, **s} for s in scores]
                conn.execute(text(ins_sql), rows)
    
    # ==================== Criterion Utilities ====================
    
    def replace_criterion_utilities(self, run_id: str, utilities: List[Dict[str, Any]]) -> None:
        """
        Replace all criterion utilities for a run.
        
        Each utility dict should have:
        - alternative_id: str (UUID)
        - criteria_id: str (UUID)
        - raw_value: float
        - utility_value: float (0.0-1.0)
        """
        del_sql = "DELETE FROM vft_criterion_utilities WHERE run_id = CAST(:run_id AS UUID)"
        ins_sql = """
        INSERT INTO vft_criterion_utilities 
        (run_id, alternative_id, criteria_id, raw_value, utility_value)
        VALUES 
        (:run_id, :alternative_id, :criteria_id, :raw_value, :utility_value)
        """
        
        with self.engine.begin() as conn:
            conn.execute(text(del_sql), {"run_id": run_id})
            if utilities:
                rows = [{"run_id": run_id, **u} for u in utilities]
                conn.execute(text(ins_sql), rows)
    
    # ==================== Weighted Utilities ====================
    
    def replace_weighted_utilities(self, run_id: str, utilities: List[Dict[str, Any]]) -> None:
        """
        Replace all weighted utilities for a run.
        
        Each utility dict should have:
        - alternative_id: str (UUID)
        - criteria_id: str (UUID)
        - weight: float
        - weighted_utility: float
        """
        del_sql = "DELETE FROM vft_weighted_utilities WHERE run_id = CAST(:run_id AS UUID)"
        ins_sql = """
        INSERT INTO vft_weighted_utilities 
        (run_id, alternative_id, criteria_id, weight, weighted_utility)
        VALUES 
        (:run_id, :alternative_id, :criteria_id, :weight, :weighted_utility)
        """
        
        with self.engine.begin() as conn:
            conn.execute(text(del_sql), {"run_id": run_id})
            if utilities:
                rows = [{"run_id": run_id, **u} for u in utilities]
                conn.execute(text(ins_sql), rows)
    
    # ==================== Result Scores ====================
    
    def replace_result_scores(self, run_id: str, scores: List[Dict[str, Any]]) -> None:
        """
        Replace all result scores (final rankings) for a run.
        
        Each score dict should have:
        - alternative_id: str (UUID)
        - total_score: float
        - rank: int (1-indexed)
        """
        del_sql = "DELETE FROM vft_result_scores WHERE run_id = CAST(:run_id AS UUID)"
        ins_sql = """
        INSERT INTO vft_result_scores 
        (run_id, alternative_id, total_score, rank)
        VALUES 
        (:run_id, :alternative_id, :total_score, :rank)
        """
        
        with self.engine.begin() as conn:
            conn.execute(text(del_sql), {"run_id": run_id})
            if scores:
                rows = [{"run_id": run_id, **s} for s in scores]
                conn.execute(text(ins_sql), rows)
