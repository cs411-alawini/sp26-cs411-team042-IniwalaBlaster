#!/usr/bin/env bash

set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <mysql-connection-args>"
  echo "Example: $0 \"-h 127.0.0.1 -P 3306 -u root -p\""
  exit 1
fi

MYSQL_ARGS=$1
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

echo "Generating seed data..."
python3 "$ROOT_DIR/scripts/generate_seed_data.py"

echo "Creating schema..."
mysql $MYSQL_ARGS < "$ROOT_DIR/sql/01_schema.sql"

echo "Loading data..."
mysql $MYSQL_ARGS < "$ROOT_DIR/sql/02_seed_data.sql"

echo "Running advanced queries..."
mysql $MYSQL_ARGS --table < "$ROOT_DIR/sql/03_advanced_queries.sql"

echo "Stage 3 setup complete."
