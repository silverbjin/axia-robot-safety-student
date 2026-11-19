"""L0 executable Git/shell acceptance for D04-D06 documented first Bash blocks.

Uses real local git/worktrees and a stub demo runner; NEVER claims ROS, WSLg,
Gazebo, camera, YOLO, safety TTL or E-Stop verification.
"""
import os
from pathlib import Path
import re
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _cmd(*args, cwd=None):
    result = subprocess.run(args, cwd=cwd, text=True, capture_output=True, timeout=20)
    assert result.returncode == 0, (args, result.stdout, result.stderr)
    return result


def _local_public_git(tmp_path):
    remote = tmp_path / "public-main.git"
    _cmd("git", "init", "-q", "--bare", "--initial-branch=main", str(remote))
    work = tmp_path / "publisher"
    _cmd("git", "init", "-q", "--initial-branch=main", str(work))
    _cmd("git", "config", "user.email", "ci@example.invalid", cwd=work)
    _cmd("git", "config", "user.name", "Guide L0 Fixture", cwd=work)
    runner = work / "block_B/day04/run_student_gazebo_yolo_once.sh"
    runner.parent.mkdir(parents=True)
    runner.write_text(
        '#!/usr/bin/env bash\n'
        'printf "mode=%s d05=%s\\n" "$1" "${AXIA_D05_LIVE:-0}" >> "$AXIA_TEST_TRACE"\n',
        encoding="utf-8",
    )
    _cmd("git", "add", ".", cwd=work)
    _cmd("git", "commit", "-qm", "minimal public student runner stub", cwd=work)
    _cmd("git", "remote", "add", "origin", str(remote), cwd=work)
    _cmd("git", "push", "-q", "-u", "origin", "main", cwd=work)
    return remote


def _first_block(name):
    guide = (ROOT / name).read_text(encoding="utf-8")
    m = re.search(r"(?ms)^~~~bash\n(.*?)\n~~~", guide)
    assert m, f"missing documented shell command: {name}"
    command = m.group(1)
    syntax = subprocess.run(["bash", "-n", "-c", command], text=True, capture_output=True)
    assert syntax.returncode == 0, (name, syntax.stderr)
    return command


def _execute(tmp_path, remote, doc, *, d04_existing_base=False):
    home = tmp_path / "home"
    home.mkdir(exist_ok=True)
    trace = tmp_path / "argv.log"
    if d04_existing_base:
        _cmd("git", "clone", "-q", str(remote), str(home / "axia-robot-safety-student-d04"))
    command = _first_block(doc).replace(
        "https://github.com/silverbjin/axia-robot-safety-student.git", str(remote)
    )
    env = dict(os.environ, HOME=str(home), AXIA_TEST_TRACE=str(trace))
    result = subprocess.run(
        ["bash", "-c", command], env=env,
        text=True, capture_output=True, timeout=25,
    )
    assert result.returncode == 0, (doc, result.stdout, result.stderr)
    assert trace.is_file(), f"{doc}: no demo runner invoked"
    lines = trace.read_text(encoding="utf-8").splitlines()
    assert any("mode=--self-check" in line for line in lines)
    assert any("mode=--run" in line for line in lines), (
        f"{doc}: first copy/paste command only did preflight; GUI never requested: {lines}"
    )
    return home, trace


@pytest.mark.parametrize("existing_base", [False, True])
def test_d04_first_command_reaches_real_run_entrypoint(tmp_path, existing_base):
    remote = _local_public_git(tmp_path)
    home, trace = _execute(
        tmp_path, remote, "day04/D04_GAZEBO_YOLO_GUI_STUDENT_GUIDE_KO.md",
        d04_existing_base=existing_base,
    )
    assert (home / "axia_d04_student_gazebo_demo_main").is_dir()
    assert "mode=--run" in trace.read_text(encoding="utf-8")
    # A second invocation must reuse clean checkout (no destructive reset).
    _execute(
        tmp_path, remote, "day04/D04_GAZEBO_YOLO_GUI_STUDENT_GUIDE_KO.md",
        d04_existing_base=False,
    )


@pytest.mark.parametrize("doc,folder", [
    ("day05/D05_STUDENT_GAZEBO_LIVE_GUIDE_KO.md", "axia_d05_student_gazebo_live_main"),
    ("day06/D06_STUDENT_LIVE_DEMO_GUIDE_20261116_KO.md", "axia_d06_student_gazebo_live_main"),
])
def test_d05_d06_first_command_uses_current_main_and_launches(tmp_path, doc, folder):
    remote = _local_public_git(tmp_path)
    home, trace = _execute(tmp_path, remote, doc)
    assert (home / folder).is_dir()
    assert "mode=--run d05=1" in trace.read_text(encoding="utf-8")
    source = (ROOT / doc).read_text(encoding="utf-8")
    assert "git clone" in source and "main" in source
    assert "1c03c9bfb4b41e2726a7c1d2f47d65496bdaa474" not in _first_block(doc)
