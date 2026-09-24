#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
export PYTHONPATH="$PWD"
python3 generate_models.py
python3 run_tests.py | tee results/tests.log
python3 run_experiments.py | tee results/experiments.log
for m in models/*.json; do n=$(basename "$m" .json); python3 verify.py "$m" "results/certificates/$n.json" >/dev/null; done
python3 quality_gate.py
python3 coverage_gate.py
python3 static_audit.py
python3 run_scaling.py
python3 blind_review_gate.py
test -s results/BLIND_REVIEW_CODE_PASS.json
