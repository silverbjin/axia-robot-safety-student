#!/usr/bin/env bash
# C-01 contract only: no ROS source, goal, motion, Gazebo, or global kill.
set -Eeuo pipefail
MODE="${1:---check}"
[[ "$#" -le 1 ]] || { echo C01_USAGE_ERROR >&2; exit 2; }
case "$MODE" in --doctor|--check) ;; *) echo C01_USAGE_ERROR >&2; exit 2;; esac
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
FIX="$ROOT/fixtures"
if ! command -v python3 >/dev/null 2>&1; then echo C01_ENV_BLOCKED_PYTHON_MISSING >&2; exit 2; fi
PY_VER="$(python3 -c 'import sys;print(".".join(map(str,sys.version_info[:3])))')"
if ! python3 -c 'import sys;sys.exit(0 if sys.version_info[:2] == (3,12) else 2)'; then
  echo "C01_ENV_DIFF_BLOCKED expected_python=3.12 actual=$PY_VER" >&2; exit 2
fi
if ! python3 -m pytest --version >/dev/null 2>&1; then echo C01_ENV_BLOCKED_PYTEST_MISSING >&2; exit 2; fi
printf 'C01_DOCTOR python=%s ros_required=false gazebo_required=false\n' "$PY_VER"
if [[ "$MODE" == --doctor ]]; then exit 0; fi
if [[ -f "$ROOT/tests/test_data_contract.py" ]]; then
 TEST="$ROOT/tests/test_data_contract.py"
elif [[ -f "$ROOT/tests/test_c01_public.py" ]]; then
 TEST="$ROOT/tests/test_c01_public.py"
else echo C01_ENV_BLOCKED_TEST_MISSING >&2; exit 2; fi
RUN="${AXIA_C01_EVIDENCE_DIR:-${HOME:-/tmp}/axia_c01_evidence/$(date -u +%Y%m%dT%H%M%SZ)-$$}"
mkdir -p -- "$RUN"
python3 "$FIX/generator.py" --check --fixture-dir "$FIX" >"$RUN/generator.stdout.log" 2>"$RUN/generator.stderr.log" || {
 cat "$RUN/generator.stderr.log" >&2; echo C01_CONTRACT_FAIL; exit 1; }
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -q "$TEST" --junitxml="$RUN/pytest.xml" >"$RUN/pytest.stdout.log" 2>"$RUN/pytest.stderr.log" || {
 cat "$RUN/pytest.stdout.log"; cat "$RUN/pytest.stderr.log" >&2; echo C01_TEST_FAIL; exit 1; }
C01_GIT_SHA="$(git -C "$ROOT" rev-parse HEAD 2>/dev/null || true)"
cp "$FIX/SHA256SUMS" "$RUN/SHA256SUMS"
python3 - "$RUN" "$C01_GIT_SHA" "$PY_VER" <<'PYVERDICT'
import json, sys
from pathlib import Path
run, sha, python = sys.argv[1:]
result = {
    'status': 'PASS', 'level': 'PYTHON_L0', 'source': 'SYNTHETIC_COURSE_FIXTURE',
    'source_sha': sha or None, 'python': python, 'traces': 46, 'rows': 4599,
    'ros_actual': False, 'gazebo_actual': False, 'owner_wsl2_verified': False,
    'artifact_files': ['SHA256SUMS', 'generator.stdout.log', 'generator.stderr.log',
                       'pytest.stdout.log', 'pytest.stderr.log', 'pytest.xml']
}
Path(run, 'verdict.json').write_text(json.dumps(result, sort_keys=True, indent=2)+'\n')
PYVERDICT
cat "$RUN/generator.stdout.log" "$RUN/pytest.stdout.log"
printf 'C01_FIXTURE_CONTRACT_PASS level=PYTHON_L0 traces=46 rows=4599 evidence=%s\n' "$RUN"
