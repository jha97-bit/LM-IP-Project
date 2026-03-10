"""
VFT Read Repository — provides read access to persisted VFT run data.
Analogous to topsis_read_repo.py in the TOPSIS model.
"""
from typing import Dict, Any, Optional, List

import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine


class VftReadRepo:
    """Read-only queries for inspecting a completed VFT run."""

    def __init__(self, engine: Engine):
        self.engine = engine

    # -------------------- run metadata --------------------

    def get_run_config(self, run_id: str) -> Optional[Dict[str, Any]]:
        sql = """
        SELECT run_id::text AS run_id, scaling_type, output_min, output_max
        FROM vft_run_config
        WHERE run_id = CAST(:run_id AS UUID)
        """
        with self.engine.begin() as conn:
            row = conn.execute(text(sql), {"run_id": run_id}).mappings().first()
        return dict(row) if row else None

    # -------------------- criteria --------------------

    def get_criteria(self, run_id: str) -> pd.DataFrame:
        sql = """
        SELECT criteria_id::text AS criteria_id, name, weight, swing_weight,
               min_val, max_val, scaling_direction, scaling_type
        FROM vft_criteria
        WHERE run_id = CAST(:run_id AS UUID)
        ORDER BY name
        """
        with self.engine.begin() as conn:
            rows = conn.execute(text(sql), {"run_id": run_id}).mappings().all()
        return pd.DataFrame([dict(r) for r in rows])

    # -------------------- alternatives --------------------

    def get_alternatives(self, run_id: str) -> pd.DataFrame:
        sql = """
        SELECT alternative_id::text AS alternative_id, name
        FROM vft_alternatives
        WHERE run_id = CAST(:run_id AS UUID)
        ORDER BY name
        """
        with self.engine.begin() as conn:
            rows = conn.execute(text(sql), {"run_id": run_id}).mappings().all()
        return pd.DataFrame([dict(r) for r in rows])

    # -------------------- raw scores --------------------

    def get_raw_scores_matrix(self, run_id: str) -> pd.DataFrame:
        """Pivoted matrix: index=alternative name, columns=criterion name, values=raw value."""
        sql = """
        SELECT a.name AS alternative, c.name AS criterion, s.value
        FROM vft_raw_scores s
        JOIN vft_alternatives a ON a.alternative_id = s.alternative_id
        JOIN vft_criteria c ON c.criteria_id = s.criteria_id
        WHERE s.run_id = CAST(:run_id AS UUID)
        """
        with self.engine.begin() as conn:
            rows = conn.execute(text(sql), {"run_id": run_id}).mappings().all()
        if not rows:
            return pd.DataFrame()
        df = pd.DataFrame([dict(r) for r in rows])
        return df.pivot(index="alternative", columns="criterion", values="value")

    # -------------------- criterion utilities --------------------

    def get_criterion_utilities(self, run_id: str) -> pd.DataFrame:
        """Flat table: alternative, criterion, raw_value, utility_value."""
        sql = """
        SELECT a.name AS alternative, c.name AS criterion,
               u.raw_value, u.utility_value
        FROM vft_criterion_utilities u
        JOIN vft_alternatives a ON a.alternative_id = u.alternative_id
        JOIN vft_criteria c ON c.criteria_id = u.criteria_id
        WHERE u.run_id = CAST(:run_id AS UUID)
        ORDER BY a.name, c.name
        """
        with self.engine.begin() as conn:
            rows = conn.execute(text(sql), {"run_id": run_id}).mappings().all()
        return pd.DataFrame([dict(r) for r in rows])

    def get_utility_matrix(self, run_id: str) -> pd.DataFrame:
        """Pivoted: index=alternative, columns=criterion, values=utility_value (0-1)."""
        sql = """
        SELECT a.name AS alternative, c.name AS criterion, u.utility_value
        FROM vft_criterion_utilities u
        JOIN vft_alternatives a ON a.alternative_id = u.alternative_id
        JOIN vft_criteria c ON c.criteria_id = u.criteria_id
        WHERE u.run_id = CAST(:run_id AS UUID)
        """
        with self.engine.begin() as conn:
            rows = conn.execute(text(sql), {"run_id": run_id}).mappings().all()
        if not rows:
            return pd.DataFrame()
        df = pd.DataFrame([dict(r) for r in rows])
        return df.pivot(index="alternative", columns="criterion", values="utility_value")

    # -------------------- weighted utilities --------------------

    def get_weighted_utilities(self, run_id: str) -> pd.DataFrame:
        """Flat table: alternative, criterion, weight, weighted_utility."""
        sql = """
        SELECT a.name AS alternative, c.name AS criterion,
               wu.weight, wu.weighted_utility
        FROM vft_weighted_utilities wu
        JOIN vft_alternatives a ON a.alternative_id = wu.alternative_id
        JOIN vft_criteria c ON c.criteria_id = wu.criteria_id
        WHERE wu.run_id = CAST(:run_id AS UUID)
        ORDER BY a.name, c.name
        """
        with self.engine.begin() as conn:
            rows = conn.execute(text(sql), {"run_id": run_id}).mappings().all()
        return pd.DataFrame([dict(r) for r in rows])

    def get_weighted_utility_matrix(self, run_id: str) -> pd.DataFrame:
        """Pivoted: index=alternative, columns=criterion, values=weighted_utility."""
        sql = """
        SELECT a.name AS alternative, c.name AS criterion, wu.weighted_utility
        FROM vft_weighted_utilities wu
        JOIN vft_alternatives a ON a.alternative_id = wu.alternative_id
        JOIN vft_criteria c ON c.criteria_id = wu.criteria_id
        WHERE wu.run_id = CAST(:run_id AS UUID)
        """
        with self.engine.begin() as conn:
            rows = conn.execute(text(sql), {"run_id": run_id}).mappings().all()
        if not rows:
            return pd.DataFrame()
        df = pd.DataFrame([dict(r) for r in rows])
        return df.pivot(index="alternative", columns="criterion", values="weighted_utility")

    # -------------------- result scores --------------------

    def get_result_scores(self, run_id: str) -> pd.DataFrame:
        """Final ranking: alternative name, total_score, rank."""
        sql = """
        SELECT a.name AS alternative, rs.total_score, rs.rank
        FROM vft_result_scores rs
        JOIN vft_alternatives a ON a.alternative_id = rs.alternative_id
        WHERE rs.run_id = CAST(:run_id AS UUID)
        ORDER BY rs.rank ASC
        """
        with self.engine.begin() as conn:
            rows = conn.execute(text(sql), {"run_id": run_id}).mappings().all()
        return pd.DataFrame([dict(r) for r in rows])
