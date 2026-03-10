"""
VFT Standalone Run Repository
No dependency on shared MCDA schema (scenarios, preference_sets, etc.)
"""
from typing import List, Dict, Any
from sqlalchemy import text
from sqlalchemy.engine import Engine


class VftRunRepo:
    """Repository for VFT run metadata (standalone)."""
    
    def __init__(self, engine: Engine):
        self.engine = engine
    
    def create_run(self, executed_by: str = "", engine_version: str = "vft=0.1.0") -> str:
        """
        Create a new VFT run record.
        Returns: run_id (UUID as string)
        """
        sql = """
        INSERT INTO vft_runs (executed_by, engine_version)
        VALUES (:executed_by, :engine_version)
        RETURNING run_id::text AS run_id
        """
        with self.engine.begin() as conn:
            row = conn.execute(
                text(sql),
                {
                    "executed_by": executed_by or "",
                    "engine_version": engine_version,
                },
            ).mappings().first()
        return str(row["run_id"])
    
    def list_runs(self, limit: int = 50) -> List[Dict[str, Any]]:
        """List all VFT runs ordered by executed_at descending."""
        sql = """
        SELECT 
            run_id::text AS run_id,
            executed_at,
            executed_by,
            engine_version,
            note
        FROM vft_runs
        ORDER BY executed_at DESC
        LIMIT :limit
        """
        with self.engine.begin() as conn:
            rows = conn.execute(text(sql), {"limit": limit}).mappings().all()
        return [dict(r) for r in rows]
    
    def get_run(self, run_id: str) -> Dict[str, Any]:
        """Get a single run by ID."""
        sql = """
        SELECT 
            run_id::text AS run_id,
            executed_at,
            executed_by,
            engine_version,
            note
        FROM vft_runs
        WHERE run_id = :run_id::uuid
        """
        with self.engine.begin() as conn:
            row = conn.execute(text(sql), {"run_id": run_id}).mappings().first()
        return dict(row) if row else None
