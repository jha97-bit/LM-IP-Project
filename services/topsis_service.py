from typing import Dict, List

import numpy as np
from sqlalchemy.engine import Engine

from core.topsis import compute_topsis
from persistence.repositories.run_repo import RunRepo
from persistence.repositories.result_repo import ResultRepo
from persistence.repositories.topsis_repo import TopsisRepo
from services.scenario_service import ScenarioData


class TopsisService:
    def __init__(self, engine: Engine):
        self.engine = engine
        self.run_repo = RunRepo(engine)
        self.result_repo = ResultRepo(engine)
        self.topsis_repo = TopsisRepo(engine)

    def run_and_persist(self, scenario_id: str, preference_set_id: str, executed_by: str, data: ScenarioData) -> str:
        w = data.weights.astype(float)
        w = w / (float(w.sum()) + 1e-12)

        artifacts = compute_topsis(
            matrix=data.matrix.astype(float),
            weights=w,
            directions=data.directions,
        )

        run_id = self.run_repo.create_run(
            scenario_id=scenario_id,
            preference_set_id=preference_set_id,
            method="topsis",
            executed_by=executed_by,
        )

        self.topsis_repo.save_run_config(run_id, normalization="vector", distance="euclidean")

        alt_id_to_score = {data.alternative_ids[i]: float(artifacts.c_star[i]) for i in range(len(data.alternative_ids))}
        self.result_repo.replace_scores(run_id, alt_id_to_score)

        # Persist TOPSIS matrices/artifacts
        norm_rows: List[dict] = []
        w_rows: List[dict] = []
        ideal_rows: List[dict] = []
        dist_rows: List[dict] = []

        m, n = data.matrix.shape
        for i in range(m):
            for j in range(n):
                norm_rows.append({
                    "run_id": run_id,
                    "alternative_id": data.alternative_ids[i],
                    "criterion_id": data.criterion_ids[j],
                    "value": float(artifacts.normalized_matrix[i, j]),
                })
                w_rows.append({
                    "run_id": run_id,
                    "alternative_id": data.alternative_ids[i],
                    "criterion_id": data.criterion_ids[j],
                    "value": float(artifacts.weighted_matrix[i, j]),
                })

        for j in range(n):
            ideal_rows.append({
                "run_id": run_id,
                "criterion_id": data.criterion_ids[j],
                "pos_ideal": float(artifacts.pis[j]),
                "neg_ideal": float(artifacts.nis[j]),
            })

        for i in range(m):
            dist_rows.append({
                "run_id": run_id,
                "alternative_id": data.alternative_ids[i],
                "s_pos": float(artifacts.s_pos[i]),
                "s_neg": float(artifacts.s_neg[i]),
                "c_star": float(artifacts.c_star[i]),
            })

        self.topsis_repo.replace_normalized(run_id, norm_rows)
        self.topsis_repo.replace_weighted(run_id, w_rows)
        self.topsis_repo.replace_ideals(run_id, ideal_rows)
        self.topsis_repo.replace_distances(run_id, dist_rows)

        return run_id
