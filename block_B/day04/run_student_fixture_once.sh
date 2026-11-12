#!/usr/bin/env bash
# Public D04 CSV/TDD runner for ROS 2 Jazzy WSL2 and plain Ubuntu 24.04.
# Does NOT require ROS/Gazebo, PyYAML, ultralytics, or instructor code.
# Disables unrelated ROS launch_testing pytest11 auto-plugin discovery.
set -Eeuo pipefail

MODE="${1:---fixture}"
[[ $# -eq 0 || $# -eq 1 ]] || { echo "D04_FIXTURE_USAGE=--fixture|--red|--green|--self-check" >&2; exit 2; }
case "$MODE" in
  --fixture|--red|--green|--self-check) ;;
  *) echo "D04_FIXTURE_USAGE=--fixture|--red|--green|--self-check" >&2; exit 2 ;;
esac

REPO="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
if [[ ! -f "$REPO/block_B/tests/test_fixture_io.py" || ! -f "$REPO/block_B/block_b_todo.py" ]]; then
  echo "D04_FIXTURE_REPO_NOT_FOUND=$REPO" >&2
  exit 2
fi
if [[ "$MODE" == --self-check ]]; then
  echo "D04_FIXTURE_STATIC_PASS ROOT=$REPO ROS_NOT_RUN GAZEBO_NOT_RUN"
  exit 0
fi

PYTHON="${AXIA_D04_FIXTURE_PYTHON:-$REPO/.venv/bin/python}"
if [[ -z "${AXIA_D04_FIXTURE_PYTHON:-}" && ! -x "$PYTHON" ]]; then
  python3 -m venv "$REPO/.venv"
fi
if [[ ! -x "$PYTHON" ]]; then
  echo "D04_FIXTURE_PYTHON_MISSING=$PYTHON" >&2
  exit 2
fi
if ! "$PYTHON" -c 'from importlib.metadata import version; assert version("pytest") == "8.3.5"' >/dev/null 2>&1; then
  "$PYTHON" -m pip install --disable-pip-version-check 'pytest==8.3.5'
fi

# The ROS 2 launch_testing pytest11 plugin is external to this Python/CSV lab;
# it may import yaml or other ROS Python libraries absent from the venv.
# Scoped to this process and its children; does not change the user's shell.
export PYTEST_DISABLE_PLUGIN_AUTOLOAD=1

cd "$REPO"
case "$MODE" in
  --fixture)
    "$PYTHON" -m pytest -q block_B/tests/test_fixture_io.py
    echo "D04_FIXTURE_ISOLATED_PASS PYTEST_DISABLE_PLUGIN_AUTOLOAD=1"
    echo "D04_FIXTURE_SCOPE=SYNTHETIC_COURSE_FIXTURE ROS_GAZEBO_NOT_RUN" ;;
  --red)
    TMP="$(mktemp)"
    trap 'rm -f -- "$TMP"' EXIT
    set +e
    "$PYTHON" -m pytest -q block_B/tests/test_block_b_public.py \
      -k 'select_person or confidence or bbox' > "$TMP" 2>&1
    RC=$?
    set -e
    cat "$TMP"
    if [[ "$RC" -eq 1 ]] && grep -q 'TODO_D04_SELECT_PERSON' "$TMP"; then
      echo "D04_STUDENT_TODO_EXPECTED_RED rc=$RC"
      exit 0
    fi
    echo "D04_STUDENT_RED_NOT_AS_EXPECTED rc=$RC"
    exit 2 ;;
  --green)
    "$PYTHON" -m pytest -q block_B/tests/test_block_b_public.py \
      -k 'select_person or confidence or bbox'
    echo "D04_STUDENT_GREEN_PUBLIC_TESTS_PASS" ;;
esac
