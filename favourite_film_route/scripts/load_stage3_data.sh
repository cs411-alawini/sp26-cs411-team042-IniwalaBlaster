#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SOCKET_PATH="${SCENETRIP_DB_SOCKET:-/tmp/scenetrip-mysql-run/mysql.sock}"
PORT="${SCENETRIP_DB_PORT:-3307}"

cd "$ROOT_DIR"
python3 scripts/generate_seed_data.py
mysql -u root --socket="$SOCKET_PATH" --port="$PORT" < sql/01_schema.sql
mysql -u root --socket="$SOCKET_PATH" --port="$PORT" < sql/02_seed_data.sql

echo "Stage 3 schema and dataset loaded into MySQL."
