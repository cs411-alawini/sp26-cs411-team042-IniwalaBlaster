#!/usr/bin/env bash

set -euo pipefail

DATA_DIR="${SCENETRIP_DATA_DIR:-/tmp/scenetrip-mysql-data}"
RUN_DIR="${SCENETRIP_RUN_DIR:-/tmp/scenetrip-mysql-run}"
SOCKET_PATH="${SCENETRIP_DB_SOCKET:-$RUN_DIR/mysql.sock}"
PORT="${SCENETRIP_DB_PORT:-3307}"

mkdir -p "$DATA_DIR" "$RUN_DIR"

if [ ! -f "$DATA_DIR/auto.cnf" ]; then
  if [ -n "$(find "$DATA_DIR" -mindepth 1 -maxdepth 1 2>/dev/null)" ]; then
    echo "Cleaning incomplete MySQL temp data directory at $DATA_DIR"
    rm -rf "$DATA_DIR"/*
  fi
  echo "Initializing MySQL data directory at $DATA_DIR"
  mysqld --initialize-insecure --datadir="$DATA_DIR" --basedir=/opt/anaconda3
fi

echo "Starting MySQL on socket $SOCKET_PATH and port $PORT"
exec mysqld_safe --datadir="$DATA_DIR" --socket="$SOCKET_PATH" --port="$PORT"
