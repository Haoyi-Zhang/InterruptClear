#!/bin/sh
set -eu
cd "$(dirname "$0")"
export PYTHONHASHSEED=0
python3 verify_all.py "$@"
