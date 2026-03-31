#!/usr/bin/env python3
"""Apply a SQL migration using SQLAlchemy (no psql required).

Usage (from project root):
  PYTHONPATH=. python scripts/apply_migration.py schema/migrations/20260330_add_ahp_method.sql

Loads DATABASE_URL from .env via persistence.engine (same as the app).
"""
from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import text

# Project root = parent of scripts/
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from persistence.engine import get_engine  # noqa: E402


def split_sql_statements(sql: str) -> list[str]:
    """Split on ';' (this migration file has no semicolons inside strings)."""
    out: list[str] = []
    for raw in sql.split(";"):
        part = raw.strip()
        if not part:
            continue
        lines = [ln for ln in part.splitlines() if ln.strip() and not ln.strip().startswith("--")]
        if not lines:
            continue
        out.append("\n".join(lines))
    return out


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python scripts/apply_migration.py <path-to.sql>", file=sys.stderr)
        sys.exit(1)
    path = Path(sys.argv[1])
    if not path.is_file():
        print(f"Not found: {path}", file=sys.stderr)
        sys.exit(1)
    sql = path.read_text()
    stmts = split_sql_statements(sql)
    if not stmts:
        print("No statements found in file.", file=sys.stderr)
        sys.exit(1)
    engine = get_engine()
    with engine.begin() as conn:
        for stmt in stmts:
            conn.execute(text(stmt))
    print(f"OK — applied {len(stmts)} statement(s) from {path}")


if __name__ == "__main__":
    main()
