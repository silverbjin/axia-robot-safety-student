#!/usr/bin/env bash
# Student one-shot: EXACT same teacher single-image YOLO demo (public copy).
# CPU-only Python; NO ROS/Gazebo, Nav2 Goal, /cmd_vel or E-Stop.
# Model/photo are downloaded into local per-user cache, NEVER committed.
set -Eeuo pipefail
umask 077

MODE="${1:---run}"
[[ $# -le 1 ]] || { echo "D04_STUDENT_USAGE=--run|--doctor|--self-check" >&2; exit 2; }
case "$MODE" in
  --run|--doctor|--self-check) ;;
  *) echo "D04_STUDENT_USAGE=--run|--doctor|--self-check" >&2; exit 2 ;;
esac
REPO="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
DEMO="$REPO/block_B/day04/yolo_single_image_demo.py"
CACHE="${AXIA_D04_STUDENT_CACHE:-$HOME/.cache/axia/d04_student_yolo}"
RESULTS="${AXIA_D04_STUDENT_RESULTS:-$HOME/axia_d04_student_results}"
VENV="${AXIA_D04_STUDENT_VENV:-$HOME/.venvs/axia-d04-student-yolo}"
MODEL="$CACHE/yolo26n.pt"
IMAGE="$CACHE/bus.jpg"
IMAGE_URL='https://ultralytics.com/images/bus.jpg'
ULTRALYTICS_VERSION='8.4.211'

if [[ "$MODE" == "--self-check" ]]; then
  [[ -s "$DEMO" ]] || { echo "D04_STUDENT_DEMO_SCRIPT_MISSING=$DEMO"; exit 2; }
  echo 'D04_STUDENT_STATIC_PASS'
  echo 'D04_STUDENT_SOURCE_PATH=block_B/day04/yolo_single_image_demo.py'
  echo 'D04_STUDENT_ASSETS_LOCAL_ONLY; NO_GAZEBO NO_ROS NO_GOAL NO_CMD_VEL'
  exit 0
fi
if ! command -v python3 >/dev/null 2>&1 || ! command -v curl >/dev/null 2>&1; then
  echo 'D04_STUDENT_MISSING_TOOLS=python3_or_curl' >&2
  exit 2
fi
[[ -s "$DEMO" ]] || { echo "D04_STUDENT_DEMO_SCRIPT_MISSING=$DEMO"; exit 2; }

PYTHON="${AXIA_D04_STUDENT_PYTHON:-$VENV/bin/python}"
check_ready() {
  local missing=0
  if [[ ! -x "$PYTHON" ]] || ! "$PYTHON" -c 'from ultralytics import YOLO' >/dev/null 2>&1; then
    echo "D04_STUDENT_ULTRALYTICS_NOT_READY=$PYTHON"; missing=1
  else
    echo "D04_STUDENT_ULTRALYTICS_READY=$PYTHON"
  fi
  [[ -s "$MODEL" ]] || { echo "D04_STUDENT_MODEL_NOT_READY=$MODEL"; missing=1; }
  [[ -s "$IMAGE" ]] || { echo "D04_STUDENT_IMAGE_NOT_READY=$IMAGE"; missing=1; }
  if (( missing > 0 )); then
    echo 'D04_STUDENT_DOCTOR_BLOCKED: run --run to prepare official public assets'
    return 2
  fi
  echo 'D04_STUDENT_DOCTOR_PASS=PREREQUISITES_ONLY'
}
if [[ "$MODE" == "--doctor" ]]; then
  check_ready
  exit 0
fi

if [[ -z "${AXIA_D04_STUDENT_PYTHON:-}" ]]; then
  if [[ ! -x "$PYTHON" ]]; then
    python3 -m venv "$VENV"
  fi
  if ! "$PYTHON" -c 'from ultralytics import YOLO' >/dev/null 2>&1; then
    "$PYTHON" -m pip install --disable-pip-version-check "ultralytics==$ULTRALYTICS_VERSION"
  fi
fi
"$PYTHON" -c 'from ultralytics import YOLO; print("D04_STUDENT_ULTRALYTICS_IMPORT_OK")'
mkdir -p "$CACHE" "$RESULTS"
if [[ ! -s "$MODEL" ]]; then
  (
    cd "$CACHE"
    "$PYTHON" - <<'PY'
from pathlib import Path
from ultralytics import YOLO
YOLO("yolo26n.pt")  # official on-demand model download
assert Path("yolo26n.pt").is_file(), "Official yolo26n.pt not downloaded"
print("D04_STUDENT_OFFICIAL_WEIGHT_READY")
PY
  )
fi
if [[ ! -s "$IMAGE" ]]; then
  curl -fsSL --retry 3 --connect-timeout 15 --max-time 100 \
    "$IMAGE_URL" -o "$IMAGE.tmp"
  mv -f "$IMAGE.tmp" "$IMAGE"
fi
"$PYTHON" - "$IMAGE" <<'PY'
import sys
from PIL import Image
with Image.open(sys.argv[1]) as picture:
    picture.verify()
print("D04_STUDENT_OFFICIAL_IMAGE_READY")
PY
check_ready

OUT="$RESULTS/teacher_same_code_$(date +%Y%m%d_%H%M%S)_$$"
"$PYTHON" "$DEMO" --model "$MODEL" --image "$IMAGE" --out "$OUT"
"$PYTHON" - "$OUT" <<'PY'
import csv
import json
import sys
from pathlib import Path
root = Path(sys.argv[1])
with (root / "detections.csv").open(newline="", encoding="utf-8") as handle:
    rows = list(csv.DictReader(handle))
metadata = json.loads((root / "run_manifest.json").read_text(encoding="utf-8"))
assert len(rows) == metadata["detections"]
assert all(row["category"] == "person" for row in rows)
assert metadata["ros_verified"] is False
assert metadata["gazebo_verified"] is False
print(f"D04_STUDENT_REAL_IMAGE_LOCAL_CSV_ROWS={len(rows)}")
print(f"D04_STUDENT_REAL_IMAGE_OUTPUT={root}")
print("D04_STUDENT_INFERENCE_SCOPE=LOCAL_YOLO_CPU_ONLY")
print("D04_STUDENT_ROS_GAZEBO_NAV2_SAFETY=NOT_RUN")
PY
