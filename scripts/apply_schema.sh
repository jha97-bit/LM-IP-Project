#!/usr/bin/env bash
# scripts/apply_schema.sh
# Apply the MCDA schema to a PostgreSQL database.
#
# Usage:
#   ./scripts/apply_schema.sh [DATABASE_URL]
#
# If DATABASE_URL is not passed, it reads from the .env file in the project root.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
SCHEMA_FILE="$PROJECT_ROOT/schema/schema.sql"

# Load .env if present and no argument given
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

echo "Applying schema from: $SCHEMA_FILE"
echo "Target database: $DB_URL"
echo ""

psql "$DB_URL" -f "$SCHEMA_FILE"

echo ""
echo "Schema applied successfully."
