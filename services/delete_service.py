# services/delete_service.py
from __future__ import annotations

from dataclasses import dataclass
from sqlalchemy import text
from sqlalchemy.engine import Engine


@dataclass(frozen=True)
class DeleteResult:
    ok: bool
    message: str


class DeleteService:
    def __init__(self, engine: Engine):
        self.engine = engine

    def delete_run(self, run_id: str) -> DeleteResult:
        if not run_id:
            return DeleteResult(False, "Missing run_id")

        with self.engine.begin() as conn:
            conn.execute(text("DELETE FROM result_scores WHERE run_id = :rid"), {"rid": run_id})
            # TOPSIS
            conn.execute(text("DELETE FROM topsis_distances WHERE run_id = :rid"), {"rid": run_id})
            conn.execute(text("DELETE FROM topsis_ideals WHERE run_id = :rid"), {"rid": run_id})
            conn.execute(text("DELETE FROM topsis_normalized_values WHERE run_id = :rid"), {"rid": run_id})
            conn.execute(text("DELETE FROM topsis_weighted_values WHERE run_id = :rid"), {"rid": run_id})
            conn.execute(text("DELETE FROM topsis_run_config WHERE run_id = :rid"), {"rid": run_id})
            # VFT
            conn.execute(text("DELETE FROM vft_criterion_utilities WHERE run_id = :rid"), {"rid": run_id})
            conn.execute(text("DELETE FROM vft_weighted_utilities WHERE run_id = :rid"), {"rid": run_id})
            conn.execute(text("DELETE FROM vft_run_config WHERE run_id = :rid"), {"rid": run_id})

            res = conn.execute(text("DELETE FROM runs WHERE run_id = :rid"), {"rid": run_id})

        if res.rowcount == 0:
            return DeleteResult(False, f"No run found for run_id={run_id}")
        return DeleteResult(True, f"Deleted run {run_id}")

    def delete_scenario(self, scenario_id: str) -> DeleteResult:
        if not scenario_id:
            return DeleteResult(False, "Missing scenario_id")

        with self.engine.begin() as conn:
            # All run artifacts via cascade from runs
            run_ids = conn.execute(
                text("SELECT run_id::text FROM runs WHERE scenario_id = :sid"),
                {"sid": scenario_id},
            ).fetchall()
            for (rid,) in run_ids:
                conn.execute(text("DELETE FROM result_scores WHERE run_id = :rid"), {"rid": rid})
                conn.execute(text("DELETE FROM topsis_distances WHERE run_id = :rid"), {"rid": rid})
                conn.execute(text("DELETE FROM topsis_ideals WHERE run_id = :rid"), {"rid": rid})
                conn.execute(text("DELETE FROM topsis_normalized_values WHERE run_id = :rid"), {"rid": rid})
                conn.execute(text("DELETE FROM topsis_weighted_values WHERE run_id = :rid"), {"rid": rid})
                conn.execute(text("DELETE FROM topsis_run_config WHERE run_id = :rid"), {"rid": rid})
                conn.execute(text("DELETE FROM vft_criterion_utilities WHERE run_id = :rid"), {"rid": rid})
                conn.execute(text("DELETE FROM vft_weighted_utilities WHERE run_id = :rid"), {"rid": rid})
                conn.execute(text("DELETE FROM vft_run_config WHERE run_id = :rid"), {"rid": rid})

            conn.execute(text("DELETE FROM runs WHERE scenario_id = :sid"), {"sid": scenario_id})
            conn.execute(text("DELETE FROM criterion_weights WHERE preference_set_id IN (SELECT preference_set_id FROM preference_sets WHERE scenario_id = :sid)"), {"sid": scenario_id})
            conn.execute(text("DELETE FROM preference_sets WHERE scenario_id = :sid"), {"sid": scenario_id})
            conn.execute(text("DELETE FROM measurements WHERE scenario_id = :sid"), {"sid": scenario_id})
            conn.execute(text("DELETE FROM value_function_points WHERE value_function_id IN (SELECT value_function_id FROM value_functions WHERE scenario_id = :sid)"), {"sid": scenario_id})
            conn.execute(text("DELETE FROM value_functions WHERE scenario_id = :sid"), {"sid": scenario_id})
            conn.execute(text("DELETE FROM alternatives WHERE scenario_id = :sid"), {"sid": scenario_id})
            conn.execute(text("DELETE FROM criteria WHERE scenario_id = :sid"), {"sid": scenario_id})
            conn.execute(text("DELETE FROM scenario_validation WHERE scenario_id = :sid"), {"sid": scenario_id})
            res = conn.execute(text("DELETE FROM scenarios WHERE scenario_id = :sid"), {"sid": scenario_id})

        if res.rowcount == 0:
            return DeleteResult(False, f"No scenario found for scenario_id={scenario_id}")
        return DeleteResult(True, f"Deleted scenario {scenario_id} and all its data")

    def delete_decision(self, decision_id: str) -> DeleteResult:
        if not decision_id:
            return DeleteResult(False, "Missing decision_id")

        with self.engine.begin() as conn:
            scens = conn.execute(
                text("SELECT scenario_id::text FROM scenarios WHERE decision_id = :did"),
                {"did": decision_id},
            ).fetchall()
            for (sid,) in scens:
                self.delete_scenario(sid)

            res = conn.execute(
                text("DELETE FROM decisions WHERE decision_id = :did"), {"did": decision_id}
            )

        if res.rowcount == 0:
            return DeleteResult(False, f"No decision found for decision_id={decision_id}")
        return DeleteResult(True, f"Deleted decision {decision_id} and all its scenarios")
