#!/usr/bin/env bash
# DAY02 dual-MVP worktree checkout; no ROS, Gazebo or Goal.
set -Eeuo pipefail
ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
GOOD_SOURCE="f7edb2d126502eeeed58ae014adadc7a2096d41b"
BAD_SOURCE="a04f9a7da8d54bbd9f944d05388792cb706adf28"
BAD_RELEASE="5f4b2a0a17ff4660083e28089ed300364c4b04a6"
BAD_BRANCH="release/day02-g07-failed-l2-20261126"
if [[ "$#" -ge 1 ]]; then OUT="$1"; else OUT="$HOME/axia-day02-failed"; fi
test -d "$ROOT/.git" || test -f "$ROOT/.git" || { echo "NOT_GIT_CHECKOUT" >&2; exit 3; }
if [[ -e "$OUT" ]]; then echo "REFUSE_OVERWRITE=$OUT" >&2; exit 3; fi
test "$(git -C "$ROOT" rev-parse "HEAD:block_B/day07/h01_runtime")" = \
     "$(git -C "$ROOT" rev-parse "$GOOD_SOURCE:block_B/day07/h01_runtime")" || {
   echo "ACCEPTED_RUNTIME_TREE_DRIFT" >&2; exit 3;
 }
git -C "$ROOT" fetch --no-tags origin "refs/heads/$BAD_BRANCH"
test "$(git -C "$ROOT" rev-parse FETCH_HEAD)" = "$BAD_RELEASE" || {
  echo "FAILED_CASE_RELEASE_SHA_DRIFT" >&2; exit 3;
}
git -C "$ROOT" worktree add --detach "$OUT" "$BAD_RELEASE"
test "$(git -C "$OUT" rev-parse HEAD:block_B/day07/h01_runtime)" = \
     "$(git -C "$OUT" rev-parse "$BAD_SOURCE:block_B/day07/h01_runtime")" || {
  echo "FAILED_CASE_RUNTIME_TREE_DRIFT" >&2; exit 3;
}
python3 "$ROOT/special_lecture/day02/scripts/verify_release.py"
python3 "$OUT/special_lecture/day02/scripts/verify_failed_case.py"
echo "AXIA_DAY02_DUAL_WORKTREE_L0_READY NO_ROS_NO_GAZEBO_NO_GOAL"
printf 'SUCCESS_RUNTIME=%s\nFAILED_RUNTIME=%s\nFAILED_DIR=%s\n' "$GOOD_SOURCE" "$BAD_SOURCE" "$OUT"
