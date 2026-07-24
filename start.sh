#!/usr/bin/env bash
# One-command setup + run for DocBrain (macOS/Linux). See start.py.
set -e
cd "$(dirname "$0")"

if command -v python3 >/dev/null 2>&1; then
  exec python3 start.py
elif command -v python >/dev/null 2>&1; then
  exec python start.py
else
  echo "Python 3.11+ is required but wasn't found. Install it from https://python.org and re-run this script."
  exit 1
fi
