# services/audit_service.py
"""
Lightweight audit helpers.
Currently a stub — extend to write to an audit_log table if needed.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import text
from sqlalchemy.engine import Engine


class AuditService:
    def __init__(self, engine: Engine):
        self.engine = engine

    def log(
        self,
        event: str,
        entity_type: str,
        entity_id: Optional[str],
        performed_by: Optional[str] = None,
        detail: Optional[str] = None,
    ) -> None:
        """
        Log an audit event. No-ops gracefully if the audit_log table
        does not exist in the schema.
        """
        try:
            with self.engine.begin() as conn:
                # Check table exists
                exists = conn.execute(
                    text("""
                        SELECT 1
                        FROM information_schema.tables
                        WHERE table_schema = 'public'
                          AND table_name = 'audit_log'
                    """)
                ).first()
                if not exists:
                    return
                conn.execute(
                    text("""
                        INSERT INTO audit_log
                            (event, entity_type, entity_id, performed_by, detail, created_at)
                        VALUES
                            (:event, :entity_type, :entity_id::uuid,
                             :performed_by, :detail, :created_at)
                    """),
                    {
                        "event": event,
                        "entity_type": entity_type,
                        "entity_id": entity_id,
                        "performed_by": performed_by,
                        "detail": detail,
                        "created_at": datetime.now(timezone.utc),
                    },
                )
        except Exception:
            # Audit failures must never crash the main flow
            pass
