#!/bin/zsh
set -e

PROJECT_DIR="${0:A:h:h}"
cd "$PROJECT_DIR"

if [[ ! -x ".venv/bin/streamlit" ]]; then
  echo "找不到 Portal 執行環境。請先執行："
  echo "python3 -m venv .venv"
  echo ".venv/bin/python -m pip install -r requirements.txt"
  exit 1
fi

export ATLAS_DATA_ROOT="${ATLAS_DATA_ROOT:-$PROJECT_DIR}"
exec .venv/bin/streamlit run portal/app.py \
  --server.address 127.0.0.1 \
  --server.port "${ATLAS_PORT:-8501}"
