# services/vft_service.py
from __future__ import annotations

import hashlib
import json
import numpy as np
from typing import Optional
from sqlalchemy import text
from sqlalchemy.engine import Engine

from core.vft_model import VFTModel, Attribute, Alternative


class VFTService:
    """
    Persists VFT runs into the shared MCDA schema.
    VFT uses the same decisions/scenarios/criteria/alternatives/measurements
    tables as TOPSIS. Value functions are stored in value_functions/value_function_points.
    Results go to vft_criterion_utilities, vft_weighted_utilities, result_scores.
    """

    ENGINE_VERSION = "vft=1.0.0"

    def __init__(self, engine: Engine):
        self.engine = engine

    def compute_input_signature(
        self, matrix: np.ndarray, weights: np.ndarray, directions: list[str]
    ) -> str:
        h = hashlib.sha256()
        h.update(("dirs:" + "|".join(directions)).encode())
        h.update(np.round(matrix, 12).tobytes(order="C"))
        h.update(np.round(weights, 12).tobytes(order="C"))
        return h.hexdigest()

    def save_value_functions(
        self,
        scenario_id: str,
        crit_map: dict,  # name -> criterion_id
        attributes: list,  # list of Attribute objects
        created_by: str = "",
    ) -> None:
        """Upsert value functions into DB for all attributes."""
        with self.engine.begin() as conn:
            for attr in attributes:
                crit_id = crit_map.get(attr.name)
                if not crit_id:
                    continue

                func_type = "piecewise_linear" if attr.scaling_type == "Custom" else "linear"

                # Upsert value_function
                row = conn.execute(
                    text("""
                        SELECT value_function_id::text AS value_function_id
                        FROM value_functions
                        WHERE scenario_id = :sid AND criterion_id = :cid
                    """),
                    {"sid": scenario_id, "cid": crit_id},
                ).mappings().first()

                if row:
                    vf_id = row["value_function_id"]
                    conn.execute(
                        text("""
                            UPDATE value_functions
                            SET function_type = :ft, output_min = 0.0, output_max = 1.0,
                                created_by = :cb
                            WHERE value_function_id = :vfid
                        """),
                        {"ft": func_type, "cb": created_by, "vfid": vf_id},
                    )
                else:
                    vf_id_row = conn.execute(
                        text("""
                            INSERT INTO value_functions
                                (scenario_id, criterion_id, function_type, output_min, output_max, created_by)
                            VALUES (:sid, :cid, :ft, 0.0, 1.0, :cb)
                            RETURNING value_function_id::text AS value_function_id
                        """),
                        {"sid": scenario_id, "cid": crit_id, "ft": func_type, "cb": created_by},
                    ).mappings().first()
                    vf_id = vf_id_row["value_function_id"]

                # Delete old points, insert new
                conn.execute(
                    text("DELETE FROM value_function_points WHERE value_function_id = :vfid"),
                    {"vfid": vf_id},
                )

                if attr.scaling_type == "Custom" and attr.custom_points:
                    points = sorted(attr.custom_points, key=lambda p: p[0])
                else:
                    # Linear: two-point representation
                    if attr.scaling_direction in ("Increasing", "Maximize"):
                        points = [(attr.min_val, 0.0), (attr.max_val, 1.0)]
                    else:
                        points = [(attr.min_val, 1.0), (attr.max_val, 0.0)]

                for order, (x, y) in enumerate(points):
                    conn.execute(
                        text("""
                            INSERT INTO value_function_points
                                (value_function_id, point_order, x, y)
                            VALUES (:vfid, :ord, :x, :y)
                            ON CONFLICT (value_function_id, point_order)
                            DO UPDATE SET x = EXCLUDED.x, y = EXCLUDED.y
                        """),
                        {"vfid": vf_id, "ord": order, "x": float(x), "y": float(y)},
                    )

    def load_value_functions(self, scenario_id: str) -> dict:
        """Load value functions keyed by criterion_id."""
        with self.engine.begin() as conn:
            rows = conn.execute(
                text("""
                    SELECT vf.value_function_id::text AS value_function_id,
                           vf.criterion_id::text AS criterion_id,
                           vf.function_type,
                           c.name AS criterion_name
                    FROM value_functions vf
                    JOIN criteria c ON c.criterion_id = vf.criterion_id
                    WHERE vf.scenario_id = :sid
                """),
                {"sid": scenario_id},
            ).mappings().all()

            result = {}
            for row in rows:
                vf_id = row["value_function_id"]
                crit_name = row["criterion_name"]
                pts = conn.execute(
                    text("""
                        SELECT x, y FROM value_function_points
                        WHERE value_function_id = :vfid
                        ORDER BY point_order
                    """),
                    {"vfid": vf_id},
                ).fetchall()
                result[crit_name] = {
                    "value_function_id": vf_id,
                    "criterion_id": row["criterion_id"],
                    "function_type": row["function_type"],
                    "points": [(float(r[0]), float(r[1])) for r in pts],
                }
        return result

    def run_and_persist(
        self,
        scenario_id: str,
        preference_set_id: str,
        executed_by: str,
        matrix_df,  # pandas DataFrame, rows=alts, cols=crits
        weights: dict,  # crit_name -> weight
        attributes: list,  # Attribute objects
        alt_map: dict,  # name -> alternative_id
        crit_map: dict,  # name -> criterion_id
        run_label: Optional[str] = None,
    ) -> str:
        """Execute VFT scoring and persist results."""
        import numpy as np

        alt_names = list(matrix_df.index)
        crit_names = list(matrix_df.columns)
        attr_by_name = {a.name: a for a in attributes}

        # Compute utilities
        utility_matrix = {}
        weighted_matrix = {}
        total_scores = {}

        for alt_name in alt_names:
            utility_matrix[alt_name] = {}
            weighted_matrix[alt_name] = {}
            total = 0.0
            for crit_name in crit_names:
                raw = float(matrix_df.loc[alt_name, crit_name])
                attr = attr_by_name.get(crit_name)
                if attr:
                    u = attr.get_value(raw)
                else:
                    u = 0.0
                w = float(weights.get(crit_name, 0.0))
                utility_matrix[alt_name][crit_name] = u
                weighted_matrix[alt_name][crit_name] = u * w
                total += u * w
            total_scores[alt_name] = total

        # Compute signature
        mat = np.array([[float(matrix_df.loc[a, c]) for c in crit_names] for a in alt_names])
        w_arr = np.array([float(weights.get(c, 0.0)) for c in crit_names])
        sig = self.compute_input_signature(mat, w_arr, ["benefit"] * len(crit_names))

        with self.engine.begin() as conn:
            row = conn.execute(
                text("""
                    INSERT INTO runs
                        (scenario_id, preference_set_id, method, engine_version,
                         executed_by, input_signature, run_label)
                    VALUES (:sid, :pid, 'vft', :ev, :by, :sig, :lbl)
                    RETURNING run_id::text AS run_id
                """),
                {
                    "sid": scenario_id,
                    "pid": preference_set_id,
                    "ev": self.ENGINE_VERSION,
                    "by": executed_by,
                    "sig": sig,
                    "lbl": run_label,
                },
            ).mappings().first()
            run_id = row["run_id"]

            # vft_run_config
            conn.execute(
                text("""
                    INSERT INTO vft_run_config (run_id, output_min, output_max, missing_policy)
                    VALUES (:rid, 0.0, 1.0, 'reject')
                    ON CONFLICT (run_id) DO NOTHING
                """),
                {"rid": run_id},
            )

            # Persist utilities
            for alt_name in alt_names:
                alt_id = alt_map.get(alt_name)
                if not alt_id:
                    continue
                for crit_name in crit_names:
                    crit_id = crit_map.get(crit_name)
                    if not crit_id:
                        continue
                    raw = float(matrix_df.loc[alt_name, crit_name])
                    u = utility_matrix[alt_name][crit_name]
                    w = float(weights.get(crit_name, 0.0))
                    wu = weighted_matrix[alt_name][crit_name]

                    conn.execute(
                        text("""
                            INSERT INTO vft_criterion_utilities
                                (run_id, alternative_id, criterion_id, raw_value, utility_value)
                            VALUES (:rid, :aid, :cid, :rv, :uv)
                            ON CONFLICT (run_id, alternative_id, criterion_id)
                            DO UPDATE SET raw_value=EXCLUDED.raw_value, utility_value=EXCLUDED.utility_value
                        """),
                        {"rid": run_id, "aid": alt_id, "cid": crit_id, "rv": raw, "uv": u},
                    )
                    conn.execute(
                        text("""
                            INSERT INTO vft_weighted_utilities
                                (run_id, alternative_id, criterion_id, weight, weighted_utility)
                            VALUES (:rid, :aid, :cid, :w, :wu)
                            ON CONFLICT (run_id, alternative_id, criterion_id)
                            DO UPDATE SET weight=EXCLUDED.weight, weighted_utility=EXCLUDED.weighted_utility
                        """),
                        {"rid": run_id, "aid": alt_id, "cid": crit_id, "w": w, "wu": wu},
                    )

            # result_scores
            conn.execute(
                text("DELETE FROM result_scores WHERE run_id = :rid"),
                {"rid": run_id},
            )
            sorted_alts = sorted(total_scores.items(), key=lambda x: x[1], reverse=True)
            for rank, (alt_name, score) in enumerate(sorted_alts, start=1):
                alt_id = alt_map.get(alt_name)
                if not alt_id:
                    continue
                conn.execute(
                    text("""
                        INSERT INTO result_scores (run_id, alternative_id, score, rank)
                        VALUES (:rid, :aid, :sc, :rk)
                    """),
                    {"rid": run_id, "aid": alt_id, "sc": score, "rk": rank},
                )

        return run_id

    def get_vft_results(self, run_id: str, engine) -> dict:
        """Load all VFT result data for a run."""
        with engine.begin() as conn:
            # Scores
            scores = conn.execute(
                text("""
                    SELECT a.name AS alternative_name, rs.score, rs.rank
                    FROM result_scores rs
                    JOIN alternatives a ON a.alternative_id = rs.alternative_id
                    WHERE rs.run_id = :rid
                    ORDER BY rs.rank
                """),
                {"rid": run_id},
            ).mappings().all()

            # Criterion utilities
            utilities = conn.execute(
                text("""
                    SELECT a.name AS alternative_name, c.name AS criterion_name,
                           cu.raw_value, cu.utility_value
                    FROM vft_criterion_utilities cu
                    JOIN alternatives a ON a.alternative_id = cu.alternative_id
                    JOIN criteria c ON c.criterion_id = cu.criterion_id
                    WHERE cu.run_id = :rid
                    ORDER BY a.name, c.name
                """),
                {"rid": run_id},
            ).mappings().all()

            # Weighted utilities
            weighted = conn.execute(
                text("""
                    SELECT a.name AS alternative_name, c.name AS criterion_name,
                           wu.weight, wu.weighted_utility
                    FROM vft_weighted_utilities wu
                    JOIN alternatives a ON a.alternative_id = wu.alternative_id
                    JOIN criteria c ON c.criterion_id = wu.criterion_id
                    WHERE wu.run_id = :rid
                    ORDER BY a.name, c.name
                """),
                {"rid": run_id},
            ).mappings().all()

        return {
            "scores": [dict(r) for r in scores],
            "utilities": [dict(r) for r in utilities],
            "weighted": [dict(r) for r in weighted],
        }
