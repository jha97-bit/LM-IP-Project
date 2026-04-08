# services/scenario_share_service.py
from __future__ import annotations

import json
import gzip
import base64
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import text
from sqlalchemy.engine import Engine


class ScenarioShareService:
    """
    Handles export/import of scenario packages for colleague sharing.

    A scenario package (.mcda file) contains:
    - Decision metadata
    - Scenario metadata
    - Alternatives and criteria definitions
    - Performance matrix (measurements)
    - All preference sets and weights
    - Value function definitions (for VFT)
    - All run results (scores, utilities, TOPSIS artifacts)

    The file is a gzip-compressed JSON, base64-encoded for portability.
    """

    def __init__(self, engine: Engine):
        self.engine = engine

    def export_scenario(self, scenario_id: str) -> bytes:
        """Export a full scenario package as bytes (.mcda file)."""
        payload: dict[str, Any] = {
            "format_version": "1.1",
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "scenario_id": scenario_id,
        }

        with self.engine.begin() as conn:
            # Decision
            scen_row = conn.execute(
                text("""
                    SELECT s.scenario_id::text, s.name, s.description, s.method_type, s.created_at::text,
                           s.created_by, s.decision_id::text,
                           d.title AS decision_title, d.purpose AS decision_purpose,
                           d.owner_team
                    FROM scenarios s
                    JOIN decisions d ON d.decision_id = s.decision_id
                    WHERE s.scenario_id = :sid
                """),
                {"sid": scenario_id},
            ).mappings().first()

            if not scen_row:
                raise ValueError(f"Scenario {scenario_id} not found")

            payload["decision"] = {
                "decision_id": scen_row["decision_id"],
                "title": scen_row["decision_title"],
                "purpose": scen_row["decision_purpose"],
                "owner_team": scen_row["owner_team"],
            }
            payload["scenario"] = {
                "scenario_id": scen_row["scenario_id"],
                "name": scen_row["name"],
                "description": scen_row["description"],
                "method_type": scen_row["method_type"],
                "created_at": scen_row["created_at"],
                "created_by": scen_row["created_by"],
            }

            # Alternatives
            alts = conn.execute(
                text("""
                    SELECT alternative_id::text, name, description
                    FROM alternatives WHERE scenario_id = :sid ORDER BY created_at
                """),
                {"sid": scenario_id},
            ).mappings().all()
            payload["alternatives"] = [dict(r) for r in alts]

            # Criteria
            crits = conn.execute(
                text("""
                    SELECT criterion_id::text, name, description, direction,
                           scale_type, unit
                    FROM criteria WHERE scenario_id = :sid ORDER BY created_at
                """),
                {"sid": scenario_id},
            ).mappings().all()
            payload["criteria"] = [dict(r) for r in crits]

            # Measurements (performance matrix)
            measurements = conn.execute(
                text("""
                    SELECT a.name AS alternative_name, c.name AS criterion_name, m.value_num
                    FROM measurements m
                    JOIN alternatives a ON a.alternative_id = m.alternative_id
                    JOIN criteria c ON c.criterion_id = m.criterion_id
                    WHERE m.scenario_id = :sid
                """),
                {"sid": scenario_id},
            ).mappings().all()
            payload["measurements"] = [dict(r) for r in measurements]

            # Preference sets + weights
            psets = conn.execute(
                text("""
                    SELECT preference_set_id::text, name, type, status, created_by, note
                    FROM preference_sets WHERE scenario_id = :sid ORDER BY created_at
                """),
                {"sid": scenario_id},
            ).mappings().all()

            psets_data = []
            for ps in psets:
                ps_dict = dict(ps)
                weights = conn.execute(
                    text("""
                        SELECT c.name AS criterion_name, cw.weight
                        FROM criterion_weights cw
                        JOIN criteria c ON c.criterion_id = cw.criterion_id
                        WHERE cw.preference_set_id = :pid
                    """),
                    {"pid": ps_dict["preference_set_id"]},
                ).mappings().all()
                ps_dict["weights"] = [dict(w) for w in weights]
                psets_data.append(ps_dict)
            payload["preference_sets"] = psets_data

            # Value functions
            vfs = conn.execute(
                text("""
                    SELECT vf.value_function_id::text, c.name AS criterion_name,
                           vf.function_type, vf.output_min, vf.output_max, vf.note
                    FROM value_functions vf
                    JOIN criteria c ON c.criterion_id = vf.criterion_id
                    WHERE vf.scenario_id = :sid
                """),
                {"sid": scenario_id},
            ).mappings().all()

            vfs_data = []
            for vf in vfs:
                vf_dict = dict(vf)
                pts = conn.execute(
                    text("""
                        SELECT point_order, x, y
                        FROM value_function_points
                        WHERE value_function_id = :vfid
                        ORDER BY point_order
                    """),
                    {"vfid": vf_dict["value_function_id"]},
                ).mappings().all()
                vf_dict["points"] = [dict(p) for p in pts]
                vfs_data.append(vf_dict)
            payload["value_functions"] = vfs_data

            # Runs and results
            runs = conn.execute(
                text("""
                    SELECT run_id::text, preference_set_id::text, method,
                           engine_version, executed_at::text, executed_by,
                           run_label, input_signature
                    FROM runs WHERE scenario_id = :sid ORDER BY executed_at DESC
                """),
                {"sid": scenario_id},
            ).mappings().all()

            runs_data = []
            for run in runs:
                run_dict = dict(run)
                run_id = run_dict["run_id"]

                # Scores
                scores = conn.execute(
                    text("""
                        SELECT a.name AS alternative_name, rs.score, rs.rank
                        FROM result_scores rs
                        JOIN alternatives a ON a.alternative_id = rs.alternative_id
                        WHERE rs.run_id = :rid
                    """),
                    {"rid": run_id},
                ).mappings().all()
                run_dict["scores"] = [dict(r) for r in scores]

                if run_dict["method"] == "topsis":
                    # TOPSIS distances
                    dists = conn.execute(
                        text("""
                            SELECT a.name AS alternative_name, td.s_pos, td.s_neg, td.c_star
                            FROM topsis_distances td
                            JOIN alternatives a ON a.alternative_id = td.alternative_id
                            WHERE td.run_id = :rid
                        """),
                        {"rid": run_id},
                    ).mappings().all()
                    run_dict["topsis_distances"] = [dict(r) for r in dists]

                    ideals = conn.execute(
                        text("""
                            SELECT c.name AS criterion_name, ti.pos_ideal, ti.neg_ideal
                            FROM topsis_ideals ti
                            JOIN criteria c ON c.criterion_id = ti.criterion_id
                            WHERE ti.run_id = :rid
                        """),
                        {"rid": run_id},
                    ).mappings().all()
                    run_dict["topsis_ideals"] = [dict(r) for r in ideals]

                elif run_dict["method"] == "vft":
                    # VFT utilities
                    utils = conn.execute(
                        text("""
                            SELECT a.name AS alternative_name, c.name AS criterion_name,
                                   cu.raw_value, cu.utility_value
                            FROM vft_criterion_utilities cu
                            JOIN alternatives a ON a.alternative_id = cu.alternative_id
                            JOIN criteria c ON c.criterion_id = cu.criterion_id
                            WHERE cu.run_id = :rid
                        """),
                        {"rid": run_id},
                    ).mappings().all()
                    run_dict["vft_utilities"] = [dict(r) for r in utils]

                runs_data.append(run_dict)
            payload["runs"] = runs_data

        # Compress and encode
        json_bytes = json.dumps(payload, default=str, indent=None).encode("utf-8")
        compressed = gzip.compress(json_bytes)
        return compressed

    def import_scenario(self, file_bytes: bytes, imported_by: str = "") -> dict:
        """
        Import a scenario package. Returns info about what was created.
        If decision/scenario with same name already exists, creates with suffix.
        """
        try:
            json_bytes = gzip.decompress(file_bytes)
        except Exception:
            # Maybe raw JSON (uncompressed)
            json_bytes = file_bytes

        payload = json.loads(json_bytes.decode("utf-8"))

        if payload.get("format_version") not in {"1.0", "1.1"}:
            raise ValueError("Unsupported package format version")

        dec_data = payload["decision"]
        scen_data = payload["scenario"]
        alts_data = payload.get("alternatives", [])
        crits_data = payload.get("criteria", [])
        measurements_data = payload.get("measurements", [])
        psets_data = payload.get("preference_sets", [])
        vfs_data = payload.get("value_functions", [])
        runs_data = payload.get("runs", [])

        new_ids = {}

        with self.engine.begin() as conn:
            # Create or find decision
            existing_dec = conn.execute(
                text("SELECT decision_id::text FROM decisions WHERE title = :t LIMIT 1"),
                {"t": dec_data["title"]},
            ).mappings().first()

            if existing_dec:
                decision_id = existing_dec["decision_id"]
            else:
                row = conn.execute(
                    text("""
                        INSERT INTO decisions (title, purpose, owner_team)
                        VALUES (:t, :p, :ot)
                        RETURNING decision_id::text AS decision_id
                    """),
                    {"t": dec_data["title"], "p": dec_data.get("purpose"), "ot": dec_data.get("owner_team")},
                ).mappings().first()
                decision_id = row["decision_id"]

            new_ids["decision_id"] = decision_id

            # Create scenario (always new, with unique name)
            base_name = scen_data["name"]
            scen_name = self._unique_scenario_name(conn, decision_id, base_name)
            scenario_method = scen_data.get("method_type") or self._infer_method_type(payload)

            row = conn.execute(
                text("""
                    INSERT INTO scenarios (decision_id, name, description, method_type, created_by)
                    VALUES (:did, :nm, :desc, :mt, :cb)
                    RETURNING scenario_id::text AS scenario_id
                """),
                {
                    "did": decision_id,
                    "nm": scen_name,
                    "desc": scen_data.get("description"),
                    "mt": scenario_method,
                    "cb": imported_by or scen_data.get("created_by"),
                },
            ).mappings().first()
            scenario_id = row["scenario_id"]
            new_ids["scenario_id"] = scenario_id
            new_ids["scenario_name"] = scen_name

            # Alternatives
            alt_name_to_id = {}
            for alt in alts_data:
                row = conn.execute(
                    text("""
                        INSERT INTO alternatives (scenario_id, name, description)
                        VALUES (:sid, :nm, :desc)
                        ON CONFLICT (scenario_id, name) DO UPDATE SET description = EXCLUDED.description
                        RETURNING alternative_id::text AS alternative_id
                    """),
                    {"sid": scenario_id, "nm": alt["name"], "desc": alt.get("description")},
                ).mappings().first()
                alt_name_to_id[alt["name"]] = row["alternative_id"]

            # Criteria
            crit_name_to_id = {}
            for crit in crits_data:
                row = conn.execute(
                    text("""
                        INSERT INTO criteria (scenario_id, name, description, direction, scale_type, unit)
                        VALUES (:sid, :nm, :desc, :dir, :st, :unit)
                        ON CONFLICT (scenario_id, name) DO UPDATE
                            SET direction=EXCLUDED.direction, scale_type=EXCLUDED.scale_type, unit=EXCLUDED.unit
                        RETURNING criterion_id::text AS criterion_id
                    """),
                    {
                        "sid": scenario_id,
                        "nm": crit["name"],
                        "desc": crit.get("description"),
                        "dir": crit["direction"],
                        "st": crit["scale_type"],
                        "unit": crit.get("unit"),
                    },
                ).mappings().first()
                crit_name_to_id[crit["name"]] = row["criterion_id"]

            # Measurements
            for m in measurements_data:
                alt_id = alt_name_to_id.get(m["alternative_name"])
                crit_id = crit_name_to_id.get(m["criterion_name"])
                if not alt_id or not crit_id:
                    continue
                conn.execute(
                    text("""
                        INSERT INTO measurements (scenario_id, alternative_id, criterion_id, value_num)
                        VALUES (:sid, :aid, :cid, :val)
                        ON CONFLICT (scenario_id, alternative_id, criterion_id)
                        DO UPDATE SET value_num = EXCLUDED.value_num
                    """),
                    {"sid": scenario_id, "aid": alt_id, "cid": crit_id, "val": m["value_num"]},
                )

            # Preference sets
            pset_old_to_new = {}
            for ps in psets_data:
                old_pid = ps["preference_set_id"]
                ps_name = self._unique_pset_name(conn, scenario_id, ps["name"])
                row = conn.execute(
                    text("""
                        INSERT INTO preference_sets (scenario_id, type, name, status, created_by, note)
                        VALUES (:sid, :tp, :nm, :st, :cb, :note)
                        RETURNING preference_set_id::text AS preference_set_id
                    """),
                    {
                        "sid": scenario_id,
                        "tp": ps.get("type", "direct"),
                        "nm": ps_name,
                        "st": ps.get("status", "active"),
                        "cb": imported_by or ps.get("created_by", ""),
                        "note": ps.get("note"),
                    },
                ).mappings().first()
                new_pid = row["preference_set_id"]
                pset_old_to_new[old_pid] = new_pid

                for w in ps.get("weights", []):
                    crit_id = crit_name_to_id.get(w["criterion_name"])
                    if not crit_id:
                        continue
                    conn.execute(
                        text("""
                            INSERT INTO criterion_weights (preference_set_id, criterion_id, weight)
                            VALUES (:pid, :cid, :w)
                            ON CONFLICT (preference_set_id, criterion_id) DO UPDATE SET weight = EXCLUDED.weight
                        """),
                        {"pid": new_pid, "cid": crit_id, "w": w["weight"]},
                    )

            # Value functions
            for vf in vfs_data:
                crit_id = crit_name_to_id.get(vf["criterion_name"])
                if not crit_id:
                    continue
                vf_row = conn.execute(
                    text("""
                        INSERT INTO value_functions
                            (scenario_id, criterion_id, function_type, output_min, output_max, created_by, note)
                        VALUES (:sid, :cid, :ft, :omin, :omax, :cb, :note)
                        ON CONFLICT (scenario_id, criterion_id) DO UPDATE
                            SET function_type=EXCLUDED.function_type
                        RETURNING value_function_id::text AS value_function_id
                    """),
                    {
                        "sid": scenario_id,
                        "cid": crit_id,
                        "ft": vf.get("function_type", "linear"),
                        "omin": vf.get("output_min", 0.0),
                        "omax": vf.get("output_max", 1.0),
                        "cb": imported_by,
                        "note": vf.get("note"),
                    },
                ).mappings().first()
                vf_id = vf_row["value_function_id"]

                conn.execute(
                    text("DELETE FROM value_function_points WHERE value_function_id = :vfid"),
                    {"vfid": vf_id},
                )
                for pt in vf.get("points", []):
                    conn.execute(
                        text("""
                            INSERT INTO value_function_points (value_function_id, point_order, x, y)
                            VALUES (:vfid, :ord, :x, :y)
                            ON CONFLICT (value_function_id, point_order) DO NOTHING
                        """),
                        {"vfid": vf_id, "ord": pt["point_order"], "x": pt["x"], "y": pt["y"]},
                    )

            # Runs and results (import as read-only history)
            new_ids["runs_imported"] = 0
            for run in runs_data:
                old_pid = run.get("preference_set_id")
                new_pid = pset_old_to_new.get(old_pid)
                if not new_pid:
                    continue

                try:
                    run_row = conn.execute(
                        text("""
                            INSERT INTO runs
                                (scenario_id, preference_set_id, method, engine_version,
                                 executed_by, run_label, input_signature)
                            VALUES (:sid, :pid, :mth, :ev, :by, :lbl, :sig)
                            RETURNING run_id::text AS run_id
                        """),
                        {
                            "sid": scenario_id,
                            "pid": new_pid,
                            "mth": run.get("method", "topsis"),
                            "ev": run.get("engine_version", "imported"),
                            "by": run.get("executed_by", "") + " [imported]",
                            "lbl": run.get("run_label"),
                            "sig": run.get("input_signature"),
                        },
                    ).mappings().first()
                    run_id = run_row["run_id"]

                    # Result scores
                    for sc in run.get("scores", []):
                        alt_id = alt_name_to_id.get(sc["alternative_name"])
                        if not alt_id:
                            continue
                        conn.execute(
                            text("""
                                INSERT INTO result_scores (run_id, alternative_id, score, rank)
                                VALUES (:rid, :aid, :sc, :rk)
                                ON CONFLICT DO NOTHING
                            """),
                            {"rid": run_id, "aid": alt_id, "sc": sc["score"], "rk": sc.get("rank", 0)},
                        )

                    # TOPSIS artifacts
                    if run.get("method") == "topsis":
                        conn.execute(
                            text("""
                                INSERT INTO topsis_run_config (run_id, normalization, distance)
                                VALUES (:rid, 'vector', 'euclidean')
                                ON CONFLICT DO NOTHING
                            """),
                            {"rid": run_id},
                        )
                        for d in run.get("topsis_distances", []):
                            alt_id = alt_name_to_id.get(d["alternative_name"])
                            if not alt_id:
                                continue
                            conn.execute(
                                text("""
                                    INSERT INTO topsis_distances
                                        (run_id, alternative_id, s_pos, s_neg, c_star)
                                    VALUES (:rid, :aid, :sp, :sn, :cs)
                                    ON CONFLICT DO NOTHING
                                """),
                                {"rid": run_id, "aid": alt_id, "sp": d["s_pos"], "sn": d["s_neg"], "cs": d["c_star"]},
                            )
                        for i in run.get("topsis_ideals", []):
                            crit_id = crit_name_to_id.get(i["criterion_name"])
                            if not crit_id:
                                continue
                            conn.execute(
                                text("""
                                    INSERT INTO topsis_ideals (run_id, criterion_id, pos_ideal, neg_ideal)
                                    VALUES (:rid, :cid, :pi, :ni)
                                    ON CONFLICT DO NOTHING
                                """),
                                {"rid": run_id, "cid": crit_id, "pi": i["pos_ideal"], "ni": i["neg_ideal"]},
                            )

                    elif run.get("method") == "vft":
                        conn.execute(
                            text("""
                                INSERT INTO vft_run_config (run_id, output_min, output_max, missing_policy)
                                VALUES (:rid, 0.0, 1.0, 'reject')
                                ON CONFLICT DO NOTHING
                            """),
                            {"rid": run_id},
                        )
                        for u in run.get("vft_utilities", []):
                            alt_id = alt_name_to_id.get(u["alternative_name"])
                            crit_id = crit_name_to_id.get(u["criterion_name"])
                            if not alt_id or not crit_id:
                                continue
                            conn.execute(
                                text("""
                                    INSERT INTO vft_criterion_utilities
                                        (run_id, alternative_id, criterion_id, raw_value, utility_value)
                                    VALUES (:rid, :aid, :cid, :rv, :uv)
                                    ON CONFLICT DO NOTHING
                                """),
                                {"rid": run_id, "aid": alt_id, "cid": crit_id,
                                 "rv": u["raw_value"], "uv": u["utility_value"]},
                            )

                    new_ids["runs_imported"] += 1
                except Exception:
                    pass  # Skip problematic runs, don't fail the whole import

        return new_ids

    def _unique_scenario_name(self, conn, decision_id: str, base: str) -> str:
        existing = conn.execute(
            text("SELECT name FROM scenarios WHERE decision_id = :did"),
            {"did": decision_id},
        ).fetchall()
        existing_names = {r[0] for r in existing}
        if base not in existing_names:
            return base
        i = 2
        while True:
            cand = f"{base} (imported {i})"
            if cand not in existing_names:
                return cand
            i += 1

    def _unique_pset_name(self, conn, scenario_id: str, base: str) -> str:
        existing = conn.execute(
            text("SELECT name FROM preference_sets WHERE scenario_id = :sid"),
            {"sid": scenario_id},
        ).fetchall()
        existing_names = {r[0] for r in existing}
        if base not in existing_names:
            return base
        i = 2
        while True:
            cand = f"{base} ({i})"
            if cand not in existing_names:
                return cand
            i += 1
