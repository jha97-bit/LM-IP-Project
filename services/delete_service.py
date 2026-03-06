# app/services/delete_service.py
from __future__ import annotations

from dataclasses import dataclass
from sqlalchemy import text
from sqlalchemy.engine import Engine


@dataclass(frozen=True)
class DeleteResult:
    ok: bool
    message: str


class DeleteService:
    """
    Safe deletes with explicit child-table deletion order.
    Works even if your DB does not have ON DELETE CASCADE.
    """

    def __init__(self, engine: Engine):
        self.engine = engine

    def delete_run(self, run_id: str) -> DeleteResult:
        if not run_id:
            return DeleteResult(False, "Missing run_id")

        with self.engine.begin() as conn:
            # Delete TOPSIS artifacts first (if present)
            conn.execute(text("DELETE FROM result_scores WHERE run_id = :rid"), {"rid": run_id})
            conn.execute(text("DELETE FROM topsis_distances WHERE run_id = :rid"), {"rid": run_id})
            conn.execute(text("DELETE FROM topsis_ideals WHERE run_id = :rid"), {"rid": run_id})
            conn.execute(text("DELETE FROM topsis_normalized_values WHERE run_id = :rid"), {"rid": run_id})
            conn.execute(text("DELETE FROM topsis_weighted_values WHERE run_id = :rid"), {"rid": run_id})
            conn.execute(text("DELETE FROM topsis_run_config WHERE run_id = :rid"), {"rid": run_id})

            # Delete the run row last
            res = conn.execute(text("DELETE FROM runs WHERE run_id = :rid"), {"rid": run_id})

        if res.rowcount == 0:
            return DeleteResult(False, f"No run found for run_id={run_id}")
        return DeleteResult(True, f"Deleted run {run_id}")

    def delete_scenario(self, scenario_id: str) -> DeleteResult:
        if not scenario_id:
            return DeleteResult(False, "Missing scenario_id")

        with self.engine.begin() as conn:
            # Delete run artifacts for all runs in scenario
            conn.execute(
                text("""
                    DELETE FROM result_scores
                    WHERE run_id IN (SELECT run_id FROM runs WHERE scenario_id = :sid)
                """),
                {"sid": scenario_id},
            )
            conn.execute(
                text("""
                    DELETE FROM topsis_distances
                    WHERE run_id IN (SELECT run_id FROM runs WHERE scenario_id = :sid)
                """),
                {"sid": scenario_id},
            )
            conn.execute(
                text("""
                    DELETE FROM topsis_ideals
                    WHERE run_id IN (SELECT run_id FROM runs WHERE scenario_id = :sid)
                """),
                {"sid": scenario_id},
            )
            conn.execute(
                text("""
                    DELETE FROM topsis_normalized_values
                    WHERE run_id IN (SELECT run_id FROM runs WHERE scenario_id = :sid)
                """),
                {"sid": scenario_id},
            )
            conn.execute(
                text("""
                    DELETE FROM topsis_weighted_values
                    WHERE run_id IN (SELECT run_id FROM runs WHERE scenario_id = :sid)
                """),
                {"sid": scenario_id},
            )
            conn.execute(
                text("""
                    DELETE FROM topsis_run_config
                    WHERE run_id IN (SELECT run_id FROM runs WHERE scenario_id = :sid)
                """),
                {"sid": scenario_id},
            )

            conn.execute(text("DELETE FROM runs WHERE scenario_id = :sid"), {"sid": scenario_id})

            # Inputs and metadata
            conn.execute(text("DELETE FROM measurements WHERE scenario_id = :sid"), {"sid": scenario_id})
            conn.execute(text("DELETE FROM criteria WHERE scenario_id = :sid"), {"sid": scenario_id})
            conn.execute(text("DELETE FROM alternatives WHERE scenario_id = :sid"), {"sid": scenario_id})
            conn.execute(text("DELETE FROM preference_sets WHERE scenario_id = :sid"), {"sid": scenario_id})

            res = conn.execute(text("DELETE FROM scenarios WHERE scenario_id = :sid"), {"sid": scenario_id})

        if res.rowcount == 0:
            return DeleteResult(False, f"No scenario found for scenario_id={scenario_id}")
        return DeleteResult(True, f"Deleted scenario {scenario_id} and all related data")

    def delete_decision(self, decision_id: str) -> DeleteResult:
        if not decision_id:
            return DeleteResult(False, "Missing decision_id")

        with self.engine.begin() as conn:
            scen_ids = conn.execute(
                text("SELECT scenario_id::text AS scenario_id FROM scenarios WHERE decision_id = :did"),
                {"did": decision_id},
            ).mappings().all()

        scen_ids = [r["scenario_id"] for r in scen_ids]

        # If no scenarios, still try to delete the decision row
        for sid in scen_ids:
            r = self.delete_scenario(sid)
            if not r.ok:
                return DeleteResult(False, f"Failed to delete scenario {sid}: {r.message}")

        with self.engine.begin() as conn:
            res = conn.execute(text("DELETE FROM decisions WHERE decision_id = :did"), {"did": decision_id})

        if res.rowcount == 0:
            return DeleteResult(False, f"No decision found for decision_id={decision_id}")
        return DeleteResult(True, f"Deleted decision {decision_id} and all related data")
