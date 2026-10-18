#!/bin/bash
cd "$(dirname "$0")/.." || exit 1

if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3 was not found. Install python3 and python3-venv first."
  exit 1
fi
python3 -c 'import sys, ssl; raise SystemExit(0 if sys.version_info >= (3, 8) else 1)' || {
  echo "Python 3.8 or newer with the ssl module is required."
  exit 1
}

if [ ! -x ".venv/bin/python" ]; then
  echo "First run: creating .venv ..."
  python3 -m venv .venv || exit 1
  .venv/bin/python -m pip install --disable-pip-version-check --upgrade pip
  .venv/bin/python -m pip install --disable-pip-version-check -r requirements.txt || {
    echo "Default index failed. Retrying with the Tsinghua mirror ..."
    .venv/bin/python -m pip install --disable-pip-version-check -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple || exit 1
  }
  touch .venv/.deps-ok
fi

exec .venv/bin/python -u scripts/pickup_server.py "$@"
