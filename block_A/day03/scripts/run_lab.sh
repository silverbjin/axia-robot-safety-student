#!/usr/bin/env bash
set -Eeuo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/../../.." && pwd)"  # repository root
cd "$ROOT"
export PYTHONPATH="$ROOT/block_A/day03"
mkdir -p results/d03
cmd="${1:-help}"
case "$cmd" in
  help|-h|--help)
    echo 'usage: bash block_A/day03/scripts/run_lab.sh {inspect|red|green|run|challenges|preflight}'
    echo '  inspect: synth fixture table; runs without TODO'
    echo '  red: intentionally incomplete TODO; report fail without claiming GREEN'
    echo '  green: completed mandatory code public tests'
    echo '  run: run both mappers over fixtures (no ROS)'
    echo '  challenges: optional application challenge tests'
    echo '  preflight: check Python imports, fixture and ROS availability (no ROS execution)'
    ;;
  inspect) python3 block_A/day03/lab_runtime.py inspect ;;
  run) python3 block_A/day03/lab_runtime.py run ;;
  preflight)
    python3 --version
    python3 -m pytest --version
    python3 -m compileall -q block_A/day03
    python3 block_A/day03/lab_runtime.py inspect
    if [[ -f /opt/ros/jazzy/setup.bash ]]; then
      echo '[OPTIONAL] ROS Jazzy detected; ROS runtime NOT_RUN'
    else
      echo '[OPTIONAL] ROS Jazzy not detected; Python lab is fully supported'
    fi
    ;;
  red)
    set +e
    python3 -m pytest -q block_A/tests/test_safety_public.py block_A/tests/test_d03_adapter_public.py \
      > results/d03/red.log 2>&1
    rc=$?
    set -e
    tail -n 5 results/d03/red.log
    echo "ORIGINAL_PYTEST_EXIT=$rc"
    if [[ "$rc" -eq 1 ]] && grep -q TODO_NOT_IMPLEMENTED results/d03/red.log; then
      echo 'EXPECTED_RED_CONFIRMED (not a passing implementation)'
    else
      echo 'BLOCKED: expected initial TODO RED not reproduced (perhaps already GREEN)'
      exit 2
    fi
    ;;
  green)
    python3 -m pytest -q block_A/tests/test_safety_public.py \
      block_A/tests/test_d03_adapter_public.py \
      --junitxml=results/d03/green.xml | tee results/d03/green.log
    ;;
  challenges)
    python3 -m pytest -q block_A/tests/test_d03_challenges_public.py \
      --junitxml=results/d03/challenges.xml
    ;;
  *) echo "Unknown command: $cmd" >&2; exit 2 ;;
esac