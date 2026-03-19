#!/usr/bin/env bash
# scripts/reset_db.sh
# Drop all MCDA tables and reapply the schema from scratch.
# WARNING: This destroys ALL data. Use only in development.
#
# Usage:
#   ./scripts/reset_db.sh [DATABASE_URL]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
SCHEMA_FILE="$PROJECT_ROOT/schema/schema.sql"

# Load .env if no argument given
if [[ -z "${1:-}" ]]; then
  ENV_FILE="$PROJECT_ROOT/.env"
  if [[ -f "$ENV_FILE" ]]; then
    export $(grep -v '^#' "$ENV_FILE" | xargs)
  fi
  DB_URL="${DATABASE_URL:-}"
else
  DB_URL="$1"
fi

if [[ -z "$DB_URL" ]]; then
  echo "ERROR: No DATABASE_URL found. Pass it as argument or set it in .env."
  exit 1
fi

echo "⚠️  WARNING: This will DROP all MCDA tables in: $DB_URL"
read -p "Type 'yes' to confirm: " CONFIRM
if [[ "$CONFIRM" != "yes" ]]; then
  echo "Aborted."
  exit 0
fi

echo ""
echo "Dropping all public tables..."

psql "$DB_URL" <<'SQL'
DO $$
DECLARE
  r RECORD;
BEGIN
  FOR r IN (
    SELECT tablename FROM pg_tables WHERE schemaname = 'public'
  ) LOOP
    EXECUTE 'DROP TABLE IF EXISTS public.' || quote_ident(r.tablename) || ' CASCADE';
  END LOOP;
END $$;
SQL

echo "Re-applying schema..."
psql "$DB_URL" -f "$SCHEMA_FILE"

echo ""
echo "Database reset complete."
