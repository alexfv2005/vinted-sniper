#!/usr/bin/env bash
# Vinted sniper launcher. Sets up the venv + browser on first run, then watches.
#
#   ./run.sh "carhartt jacke"              # just a search
#   ./run.sh "carhartt jacke" 50           # search + max price
#   ./run.sh "carhartt jacke" 50 M L       # search + max price + sizes
#
# For several searches / brands / keywords use a config file:
#   ./run.sh --config config.yaml
# or call python main.py directly with its flags.

set -e
cd "$(dirname "$0")"

# first run: make the venv, install deps, download the chromium playwright drives
if [ ! -d ".venv" ]; then
    echo "First-time setup (installing dependencies + browser, ~1-2 min)..."
    python3 -m venv .venv
    ./.venv/bin/pip install -q -r requirements.txt
    ./.venv/bin/python -m playwright install chromium
fi

PY=./.venv/bin/python

# --config or any --flag? hand everything straight to main.py untouched.
if [ "$1" = "--config" ] || [[ "$1" == --* ]]; then
    exec "$PY" main.py "$@"
fi

if [ -z "$1" ]; then
    echo 'Usage: ./run.sh "search text" [max_price] [size...]'
    echo 'Example: ./run.sh "carhartt jacke" 50 M L'
    exit 1
fi

QUERY="$1"; shift
ARGS=("$QUERY")

# second positional arg, if numeric, is the max price
if [[ "$1" =~ ^[0-9]+([.][0-9]+)?$ ]]; then
    ARGS+=(--max-price "$1"); shift
fi

# whatever's left = sizes
if [ "$#" -gt 0 ]; then
    ARGS+=(--sizes "$@")
fi

exec "$PY" main.py "${ARGS[@]}"
