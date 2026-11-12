"""Public D04 guide audit: execute staged CSV commands, inspect example output.

No private instructor code; no ROS/Gazebo. The separate public workflow
runs the real YOLO image model. Expected TODO RED is never called GREEN.
"""
from __future__ import annotations

import csv
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
GUIDE = ROOT / "block_B/day04/D04_STUDENT_LAB_GUIDE_KO.md"
README = ROOT / "block_B/README_KO.md"
LAB = ROOT / "block_B/day04/LAB.md"
RUNNER = ROOT / "block_B/day04/run_student_fixture_once.sh"
YOLO_RUNNER = ROOT / "block_B/day04/run_teacher_yolo_demo_once.sh"

def flattened_bash(markdown: str) -> list[str]:
    return [match.group(2) for match in re.finditer(
        r"(?ms)^([~]{3}|\x60{3})bash\n(.*?)\n\1", markdown)]

def run(*args: str, cwd: Path, env: dict[str,str] | None = None, seconds: int=40):
    return subprocess.run(args, cwd=cwd, capture_output=True,
                          text=True, env=env, timeout=seconds)

def test_every_guide_bash_block_has_valid_syntax():
    for document in (GUIDE, README, LAB):
        source = document.read_text(encoding="utf-8")
        assert source.count("~~~") % 2 == 0
        blocks = flattened_bash(source)
        assert blocks or document == LAB
        for i, code in enumerate(blocks):
            result = run("bash", "-n", "-c", code, cwd=ROOT)
            assert result.returncode == 0, (document, i, result.stderr)

def test_all_student_documents_avoid_ros_plugin_autoload_regression():
    for doc in (GUIDE, README, LAB):
        source = doc.read_text(encoding="utf-8")
        for code in flattened_bash(source):
            for line in code.splitlines():
                if re.search(r"\b(?:python|python3)\s+-m\s+pytest\b", line):
                    assert "PYTEST_DISABLE_PLUGIN_AUTOLOAD=1" in line, (doc, line)
        if doc == LAB:
            assert "python -m pytest -q block_B/tests/test_block_b_public.py" not in source
        assert "run_student_fixture_once.sh" in source, doc

def test_student_tdd_commands_in_real_staged_order(tmp_path):
    env = os.environ.copy()
    env["AXIA_D04_FIXTURE_PYTHON"] = sys.executable
    env["PYTHONPATH"] = str(ROOT) + os.pathsep + env.get("PYTHONPATH","")
    env["HOME"] = str(tmp_path)
    steps = [
        ("--self-check", 0, "D04_FIXTURE_STATIC_PASS"),
        ("--fixture", 0, "D04_FIXTURE_ISOLATED_PASS"),
        ("--red", 0, "D04_STUDENT_TODO_EXPECTED_RED rc=1"),
        ("--green", 1, "TODO_D04_SELECT_PERSON"),
    ]
    for mode, rc, marker in steps:
        response = run("bash", str(RUNNER), mode, cwd=tmp_path, env=env)
        assert response.returncode == rc, (mode, response.stdout, response.stderr)
        assert marker in response.stdout, (mode, response.stdout)
        if mode == "--fixture":
            assert "4 passed" in response.stdout
        if mode == "--green":
            assert "D04_STUDENT_GREEN_PUBLIC_TESTS_PASS" not in response.stdout

def test_expected_f001_f002_f003_matches_fixture_without_todo_solution():
    with (ROOT / "block_B/fixtures/detections.csv").open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 4
    def chosen(frame):
        candidates = [r for r in rows if r["frame_id"] == frame
                      and r["category"] == "person"
                      and float(r["confidence"]) >= 0.5]
        return max(candidates, key=lambda r: float(r["confidence"])) if candidates else None
    assert float(chosen("f001")["confidence"]) == 0.92
    assert chosen("f002") is None
    assert float(chosen("f003")["confidence"]) == 0.80
    guide = GUIDE.read_text()
    for expected in ("f001: person 0.92", "f002: NONE", "f003: person 0.80"):
        assert expected in guide

def test_guide_yolo_result_inspection_commands_with_existing_outputs(tmp_path):
    guide = GUIDE.read_text()
    excerpt = guide.split("### 출력 직접 확인 및 코드 해설",1)[1].split("~~~bash",1)[1].split("~~~",1)[0]
    home = tmp_path / "home"
    results = home / "axia_d04_student_results" / "teacher_same_code_20261112_test"
    results.mkdir(parents=True)
    (results/"detections.csv").write_text("category,confidence\nperson,0.91\n")
    (results/"run_manifest.json").write_text('{"level":"LOCAL_YOLO_CPU_ONLY","detections":1}\n')
    env = os.environ.copy()
    env["HOME"] = str(home)
    output = run("bash", "-Eeuo", "pipefail", "-c", excerpt, cwd=ROOT,env=env)
    assert output.returncode == 0, output.stdout+output.stderr
    assert "person,0.91" in output.stdout
    assert "LOCAL_YOLO_CPU_ONLY" in output.stdout

def test_actual_yolo_is_explained_as_success_not_ros_failure():
    guide = GUIDE.read_text()
    for token in ("LOCAL_YOLO_CPU_ONLY: 4 persons",
                  "D04_STUDENT_REAL_IMAGE_LOCAL_CSV_ROWS=4",
                  "D04_STUDENT_ROS_GAZEBO_NAV2_SAFETY=NOT_RUN",
                  "실패가 아니라", "실제 YOLO"):
        assert token in guide, token
    assert "run_teacher_yolo_demo_once.sh --run" in guide
    assert YOLO_RUNNER.is_file()

def test_local_relative_markdown_links_are_valid():
    guide = GUIDE.read_text()
    for link in re.findall(r"\[[^\]]+\]\(([^)]+)\)", guide):
        if not link.startswith(("http://", "https://", "#", "mailto:")):
            assert (GUIDE.parent/link.split("#",1)[0]).exists(), link


def test_documented_clone_and_existing_checkout_keep_environment(tmp_path):
    """Run guide's FIRST fenced block as written against PUBLIC GitHub twice.

    Validates real clone/branch fetch and no deletion of existing .venv or
    user artifacts. No instructor repo, private token, ROS or Gazebo.
    """
    home = tmp_path / "home"
    home.mkdir()
    script = flattened_bash(GUIDE.read_text(encoding="utf-8"))[0]
    assert "https://github.com/silverbjin/axia-robot-safety-student.git" in script
    env = os.environ.copy()
    env["HOME"] = str(home)
    env.pop("AXIA_D04_FIXTURE_PYTHON", None)
    for attempt in (1, 2):
        result = run("bash", "-c", script, cwd=tmp_path, env=env, seconds=100)
        assert result.returncode == 0, (attempt, result.stdout, result.stderr)
        assert "4 passed" in result.stdout
        assert "D04_FIXTURE_ISOLATED_PASS" in result.stdout
        clone = home / "axia-robot-safety-student-d04"
        assert (clone / ".git").is_dir()
        assert (clone / ".venv/bin/python").is_file()
        if attempt == 1:
            (clone / ".venv" / "keep_my_lab.txt").write_text("preserve my evidence")
        else:
            assert (clone / ".venv" / "keep_my_lab.txt").read_text() == "preserve my evidence"
    checked = run("git", "-C", str(clone), "branch", "--show-current", cwd=tmp_path)
    assert checked.stdout.strip() == "feature/block-b-d04-shared-yolo-demo-20261112"
