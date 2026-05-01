#!/usr/bin/env bash
set -euo pipefail

APP_ROOT="${APP_ROOT:-/opt/render/project/src}"
PERSIST_DIR="${PERSIST_DIR:-/var/data}"

mkdir -p "${PERSIST_DIR}"
mkdir -p "${PERSIST_DIR}/reports"

if [ -e "${APP_ROOT}/data" ] && [ ! -L "${APP_ROOT}/data" ]; then
  rm -rf "${APP_ROOT}/data"
fi

if [ ! -L "${APP_ROOT}/data" ]; then
  ln -s "${PERSIST_DIR}" "${APP_ROOT}/data"
fi

export DATA_DIR="${PERSIST_DIR}"
export PORT="${PORT:-8000}"

exec uvicorn app.main:app --app-dir services/api --host 0.0.0.0 --port "${PORT}"

