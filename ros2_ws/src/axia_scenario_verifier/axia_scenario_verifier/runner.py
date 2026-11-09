"""AXIA P1-T07 evidence-first runner (no autonomous physical-robot control).

Profiles UNIT and ROS_FAKE collect *partial* verification; they never accept
G02/G03/G04 as Gazebo E2E. Gazebo profile BLOCKED until T08 final harness.
Only spawned process groups are signalled. No global pkill or goal publishing.
"""
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import argparse
import csv
import hashlib
import json
import os
import shutil
import signal
import subprocess
import sys
import time
import uuid
import xml.etree.ElementTree as ET

from .ros_isolation import run_isolated_ros_cases

EXIT_PASS, EXIT_FAIL, EXIT_BLOCKED, EXIT_INCONCLUSIVE, EXIT_ERROR = 0, 1, 2, 3, 4
GATES = ("G02", "G03", "G04")
ROOT = Path(__file__).resolve().parents[4]


@dataclass(frozen=True)
class StageSpec:
    stage_id: str
    gate: str
    paths: tuple[str, ...]
    required: frozenset[str]
    scope: str


UNIT_STAGES = (
    StageSpec("G02_UNIT", "G02", (
        "tests/unit/test_p1_fsm.py",
        "tests/unit/test_p1_fixture_runner.py",
        "tests/unit/test_p1_command_gate.py",
        "tests/unit/test_p1_nav2_cancel_client.py",
    ), frozenset({
        "test_fixture_schema_and_all_cases_unique",
        "test_t04_original_stop_cause_survives_later_cancel_ack_event",
        "test_u01_boot_safe_disarmed",
    }), "UNIT"),
    StageSpec("G04_UNIT", "G04", (
        "tests/unit/test_p1_watchdog.py",
        "tests/unit/test_p1_t06_fault_policy.py",
    ), frozenset({
        "test_scan_timeout_monotonic_receive_time",
        "test_clock_freeze_detected_in_host_monotonic_domain",
        "test_dropped_scan_has_no_output",
    }), "UNIT"),
)
ROS_STAGES = (
    StageSpec("G03_ROS_FAKE", "G03", (
        "tests/ros_integration/test_p1_t04_action.py",
    ), frozenset({
        "test_action_cancel_ack_is_not_terminal_and_goal_uuid_matched",
        "test_supervisor_goal_stop_cancel_reset_rearm_has_no_auto_resume",
        "test_p1_t05_cm_graph_exists_but_lifecycle_not_active_blocks_start",
    }), "ROS_FAKE"),
    StageSpec("G04_ROS_FAKE", "G04", (
        "tests/ros_integration/test_p1_t06_faults.py",
    ), frozenset({
        "test_t06_lost_scans_protective_stop_and_cancel",
        "test_t06_repeated_old_stamp_protective_stop_and_cancel",
        "test_t06_future_stamp_protective_stop_and_cancel",
        "test_t06_clock_freeze_still_publishes_zero_on_steady_timer",
        "test_t06_command_heartbeat_loss_and_no_automatic_resume",
        "test_t06_injection_controls_disabled_are_fail_closed",
        "test_t06_scan_recovery_does_not_rearm_without_manual_reset",
    }), "ROS_FAKE"),
)


def choose_stages(profile: str) -> tuple[StageSpec, ...]:
    if profile == "unit":
        return UNIT_STAGES
    if profile == "ros-fake":
        return UNIT_STAGES + ROS_STAGES
    if profile == "gazebo-e2e":
        raise ValueError("Gazebo E2E is not implemented in T07; requires T08 WSL2 acceptance")
    raise ValueError("unknown profile")


def create_run_id() -> str:
    return "p1-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def atomic_json(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    temp.write_text(json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8")
    temp.replace(path)


def classify_junit(path: Path, *, returncode: int,
                   required: set[str] | frozenset[str]) -> dict:
    result = {
        "status": "INCONCLUSIVE", "exit_code": EXIT_INCONCLUSIVE,
        "tests": 0, "failures": 0, "skipped": 0,
        "missing_tests": sorted(required), "junit_present": path.is_file(),
    }
    if not path.is_file():
        if returncode not in (0, 5):
            result.update(status="FAIL", exit_code=EXIT_FAIL)
        return result
    try:
        xml = ET.parse(path)
        cases = list(xml.getroot().iter("testcase"))
    except (ET.ParseError, OSError, ValueError) as exc:
        result["reason"] = "INVALID_JUNIT_" + type(exc).__name__
        return result
    names = {c.attrib.get("name", "").split("[")[0] for c in cases
             if not any(e.tag == "skipped" for e in c)}
    failed = sum(any(e.tag in ("error", "failure") for e in c) for c in cases)
    skipped = sum(any(e.tag == "skipped" for e in c) for c in cases)
    result.update(tests=len(cases), failures=failed, skipped=skipped,
                  missing_tests=sorted(set(required) - names))
    if failed or returncode not in (0, 5):
        result.update(status="FAIL", exit_code=EXIT_FAIL)
    elif not cases or result["missing_tests"] or skipped or returncode == 5:
        result.update(status="INCONCLUSIVE", exit_code=EXIT_INCONCLUSIVE)
    else:
        result.update(status="PASS", exit_code=EXIT_PASS)
    return result


def gate_verdicts(profile: str, stage_results: dict) -> dict:
    stages = choose_stages(profile) if profile != "gazebo-e2e" else ()
    gates = {}
    for gate in GATES:
        belonging = [s for s in stages if s.gate == gate]
        states = [stage_results.get(s.stage_id, {}).get("status", "NOT_RUN")
                  for s in belonging]
        if "FAIL" in states:
            state = "FAIL"
        elif "ERROR" in states:
            state = "ERROR"
        elif "BLOCKED" in states:
            state = "BLOCKED"
        elif "INCONCLUSIVE" in states:
            state = "INCONCLUSIVE"
        elif not states or "NOT_RUN" in states:
            state = "NOT_RUN"
        elif states and all(x == "PASS" for x in states):
            state = ("ROS_FAKE_INTEGRATION_PASS"
                     if any(s.scope == "ROS_FAKE" for s in belonging)
                     else "UNIT_SUBSET_PASS")
        else:
            state = "INCONCLUSIVE"
        gates[gate] = {
            "status": state,
            "gate_accepted": False,
            "required_stages": [s.stage_id for s in belonging],
            "observed_stages": states,
        }
    return gates


def _git_sha(repo: Path) -> str | None:
    # GitHub container checkout is often owned by a different uid. Configure
    # safe.directory only for this single read-only Git invocation.
    try:
        p = subprocess.run(
            ["git", "-c", "safe.directory=" + str(repo.resolve()),
             "-C", str(repo.resolve()), "rev-parse", "--verify", "HEAD"],
            capture_output=True, text=True, timeout=5, check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    value = p.stdout.strip() if p.returncode == 0 else ""
    if len(value) != 40 or any(x not in "0123456789abcdef" for x in value.lower()):
        return None
    expected = os.environ.get("GITHUB_SHA", "")
    if expected and expected.lower() != value.lower():
        return None  # CI workspace/commit mismatch; never silently substitute.
    return value.lower()


def _environment(profile: str, *, repeat: int) -> tuple[dict, str | None]:
    data = {
        "profile": profile, "repeat": repeat, "python_version": sys.version.split()[0],
        "ros_distro": os.getenv("ROS_DISTRO"), "ci": bool(os.getenv("CI")),
        "os_name": os.name, "certified_estop_verified": False,
    }
    if profile == "gazebo-e2e":
        return data, "T08_GAZEBO_RUNNER_NOT_IMPLEMENTED"
    if profile == "ros-fake":
        if os.getenv("ROS_DISTRO") != "jazzy":
            return data, "ROS_JAZZY_NOT_SOURCED"
        try:
            import rclpy  # real middleware required for fake Nav2 graph tests
            from nav2_msgs.action import NavigateToPose  # noqa: F401
            data["rmw_implementation"] = rclpy.get_rmw_implementation_identifier()
        except ImportError as exc:
            return data, "ROS_ACTION_DEPENDENCY_MISSING:" + str(exc)
    return data, None


def _terminate_owned_process(proc: subprocess.Popen) -> None:
    if proc.poll() is not None:
        return
    try:
        if os.name == "posix":
            os.killpg(proc.pid, signal.SIGTERM)
        else:
            proc.terminate()
        proc.wait(timeout=3)
    except (ProcessLookupError, subprocess.TimeoutExpired):
        if proc.poll() is None:
            if os.name == "posix":
                os.killpg(proc.pid, signal.SIGKILL)
            else:
                proc.kill()
            proc.wait(timeout=3)


def _append_event(path: Path, event: dict) -> None:
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(event, sort_keys=True, ensure_ascii=False) + "\n")


def execute_stage(spec: StageSpec, *, run_dir: Path, repeat_no: int,
                  timeout_sec: float, root: Path,
                  used_domains: set[int] | None = None) -> dict:
    dest = run_dir / spec.gate / ("run_%02d" % repeat_no) / spec.stage_id
    dest.mkdir(parents=True, exist_ok=False)
    events = dest / "events.jsonl"
    xml_path = dest / "pytest.xml"
    args = [sys.executable, "-m", "pytest", "-q", "-ra", *spec.paths,
            "--junitxml=" + str(xml_path)]
    env = os.environ.copy()
    pkg_dirs = [str(root / "ros2_ws/src" / pkg) for pkg in (
        "axia_safety_supervisor", "axia_fault_injector", "axia_scenario_verifier"
    )]
    env["PYTHONPATH"] = os.pathsep.join(pkg_dirs + ([env["PYTHONPATH"]] if env.get("PYTHONPATH") else []))
    if spec.scope == "ROS_FAKE":
        # Each individual test gets a fresh domain AND a fresh process.
        # Do not use deprecated ROS_LOCALHOST_ONLY, even if user exported it.
        env.pop("ROS_LOCALHOST_ONLY", None)
        env.pop("ROS_STATIC_PEERS", None)
        env["ROS_AUTOMATIC_DISCOVERY_RANGE"] = "LOCALHOST"
        env.pop("ROS_DOMAIN_ID", None)
    meta = {"stage": spec.stage_id, "gate": spec.gate, "scope": spec.scope,
            "repeat": repeat_no, "domain_id": env.get("ROS_DOMAIN_ID"),
            "argv": args, "timeout_sec": timeout_sec}
    atomic_json(dest / "process_state.json", {"status": "STARTING", **meta})
    start = time.monotonic_ns()
    _append_event(events, {"event": "START", "steady_ns": start, "stage": spec.stage_id})
    rc = EXIT_ERROR
    timed_out = False
    proc = None
    isolated = None
    try:
        if spec.scope == "ROS_FAKE":
            isolated = run_isolated_ros_cases(
                [root / p for p in spec.paths], dest=dest, root=root,
                timeout_sec=timeout_sec, env=env,
                used_domains=used_domains if used_domains is not None else set(),
            )
            rc = isolated["returncode"]
            timed_out = isolated["timed_out"]
        else:
            with (dest / "stdout.log").open("w", encoding="utf-8") as stdout, (
                    dest / "stderr.log").open("w", encoding="utf-8") as stderr:
                proc = subprocess.Popen(args, cwd=root, env=env, stdout=stdout,
                                        stderr=stderr, start_new_session=True)
                try:
                    rc = proc.wait(timeout=timeout_sec)
                except subprocess.TimeoutExpired:
                    timed_out = True
                    _terminate_owned_process(proc)
                    rc = 124
    except (OSError, ValueError, RuntimeError) as exc:
        (dest / "runner_error.txt").write_text(type(exc).__name__ + ": " + str(exc))
        rc = EXIT_ERROR
    finally:
        if proc is not None:
            _terminate_owned_process(proc)
    finish = time.monotonic_ns()
    outcome = classify_junit(xml_path, returncode=rc, required=spec.required)
    if timed_out:
        outcome.update(status="FAIL", exit_code=EXIT_FAIL, reason="TIMEOUT")
    if (dest / "runner_error.txt").is_file():
        outcome.update(status="ERROR", exit_code=EXIT_ERROR, reason="SUBPROCESS_ERROR")
    outcome.update(stage_id=spec.stage_id, gate=spec.gate, scope=spec.scope,
                   repeat=repeat_no, returncode=rc, elapsed_steady_ns=finish-start,
                   case_isolation=("PROCESS_AND_DOMAIN" if isolated else None),
                   case_results=(isolated["cases"] if isolated else []),
                   junit_sha256=sha256(xml_path) if xml_path.is_file() else None)
    atomic_json(dest / "result.json", outcome)
    atomic_json(dest / "process_state.json",
                {"status": "EXITED", "returncode": rc, "timed_out": timed_out,
                 "elapsed_steady_ns": finish-start, **meta})
    _append_event(events, {"event": "FINISH", "steady_ns": finish,
                           "status": outcome["status"], "returncode": rc})
    return outcome


def _combined_junit(run_dir: Path, stages: list[dict]) -> None:
    root_xml = ET.Element("testsuites")
    for stage in stages:
        path = (run_dir / stage["gate"] / ("run_%02d" % stage["repeat"]) /
                stage["stage_id"] / "pytest.xml")
        if path.is_file():
            try:
                root = ET.parse(path).getroot()
                for suite in root.iter("testsuite"):
                    # Keep only direct leaf suites, avoid accidental double counting.
                    if not any(ch.tag == "testsuite" for ch in suite):
                        root_xml.append(suite)
                continue
            except (ET.ParseError, OSError):
                pass
        # This is a runner evidence error, never a fabricated passing test.
        suite = ET.SubElement(root_xml, "testsuite", name=stage["stage_id"],
                              tests="1", errors="1")
        case = ET.SubElement(suite, "testcase", name="RUNNER_EVIDENCE_MISSING")
        ET.SubElement(case, "error", message=stage["status"])
    ET.ElementTree(root_xml).write(run_dir / "junit.xml", encoding="utf-8",
                                   xml_declaration=True)


def _evidence_index(run_dir: Path) -> None:
    files = sorted(f for f in run_dir.rglob("*") if f.is_file()
                   and f.name not in ("checksums.sha256", "checksums.sha256.tmp"))
    lines = [sha256(path) + "  " + path.relative_to(run_dir).as_posix()
             for path in files]
    (run_dir / "checksums.sha256").write_text("\n".join(lines) + "\n",
                                              encoding="utf-8")


def _stage_summary(results: list[dict], stages: tuple[StageSpec, ...]) -> dict:
    status_map = {}
    for s in stages:
        values = [x["status"] for x in results if x["stage_id"] == s.stage_id]
        if not values:
            status_map[s.stage_id] = {"status": "NOT_RUN"}
        else:
            status = next((v for v in ("FAIL", "ERROR", "BLOCKED", "INCONCLUSIVE")
                           if v in values), "PASS")
            status_map[s.stage_id] = {"status": status, "runs": len(values)}
    return status_map


def run(profile: str, *, repeat: int = 1, results_root: Path | str = "results/p1",
        timeout_sec: float = 120, allow_partial_ci: bool = False,
        root: Path = ROOT) -> tuple[int, Path]:
    if repeat < 1 or repeat > 20 or timeout_sec <= 0:
        raise ValueError("repeat must be 1..20 and timeout-sec positive")
    if allow_partial_ci and profile not in ("unit", "ros-fake"):
        raise ValueError("partial CI mode only for synthetic/unit validation")
    result_dir = Path(results_root).resolve() / create_run_id()
    result_dir.mkdir(parents=True, exist_ok=False)
    start_ns = time.monotonic_ns()
    metadata, blocked = _environment(profile, repeat=repeat)
    basepath = root / "docs/baselines/AXIA_Robot_Safety_MVP_Baseline_Scenario_Acceptance_v1_KO.md"
    inputpaths = [basepath, root / "fixtures/p1/g02_fsm_cases.yaml"]
    for st in UNIT_STAGES + ROS_STAGES:
        inputpaths.extend(root / p for p in st.paths)
    git_commit = _git_sha(root)
    if not blocked and git_commit is None:
        blocked = "SOURCE_COMMIT_MISSING_OR_CI_MISMATCH"
    manifest = {
        **metadata, "run_id": result_dir.name,
        "source_commit": git_commit,
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "input_sha256": {str(p.relative_to(root)): sha256(p) for p in set(inputpaths)
                         if p.is_file()},
        "source_root": str(root), "scope": "NOT_GAZEBO_E2E",
        "no_safety_certification": True,
    }
    atomic_json(result_dir / "manifest.json", manifest)
    stage_results: list[dict] = []
    used_domains: set[int] = set()
    specs = ()
    if not blocked:
        specs = choose_stages(profile)
        for iteration in range(1, repeat + 1):
            for spec in specs:
                stage_results.append(execute_stage(
                    spec, run_dir=result_dir, repeat_no=iteration,
                    timeout_sec=timeout_sec, root=root,
                    used_domains=used_domains,
                ))
    stages = _stage_summary(stage_results, specs)
    gates = gate_verdicts(profile, stages)
    if blocked:
        verdict = "BLOCKED"
        code = EXIT_BLOCKED
    elif any(x["status"] == "FAIL" for x in stage_results):
        verdict, code = "FAIL", EXIT_FAIL
    elif any(x["status"] == "ERROR" for x in stage_results):
        verdict, code = "ERROR", EXIT_ERROR
    elif not stage_results or any(x["status"] != "PASS" for x in stage_results):
        verdict, code = "INCONCLUSIVE", EXIT_INCONCLUSIVE
    else:
        verdict, code = "PARTIAL_VERIFIED", (EXIT_PASS if allow_partial_ci
                                             else EXIT_INCONCLUSIVE)
    metrics = result_dir / "metrics.csv"
    with metrics.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(("gate", "stage", "repeat", "t_fault_monotonic_ns",
                         "t_diagnose_monotonic_ns", "t_cmd_zero_monotonic_ns",
                         "t_odom_stop_monotonic_ns", "measurement_status"))
        for item in stage_results:
            writer.writerow((item["gate"], item["stage_id"], item["repeat"],
                             "", "", "", "", "NOT_MEASURED"))
    summary = {
        "profile": profile, "run_id": result_dir.name, "overall_status": verdict,
        "exit_code": code, "blocked_reason": blocked,
        "stages": stages, "stage_results": stage_results,
        "gates": gates, "gate_accepted": False, "gazebo_executed": False,
        "certified_estop_verified": False, "rosbag2_evidence": "NOT_CAPTURED",
        "odom_stop_evidence": "NOT_MEASURED",
        "elapsed_steady_ns": time.monotonic_ns()-start_ns,
    }
    atomic_json(result_dir / "summary.json", summary)
    (result_dir / "summary.md").write_text(
        "# AXIA P1 T07 evidence — " + verdict + "\n\n"
        + f"Profile: {profile}; source: {manifest['source_commit']}; run: {result_dir.name}\n\n"
        + "G02/G03/G04 final acceptance: **NOT_ACCEPTED** (no Gazebo evidence).\n\n"
        + ("Blocked reason: " + blocked + "\n\n" if blocked else "")
        + "\n".join(f"- {gate}: {g['status']}; accepted=false"
                    for gate,g in gates.items()) + "\n\n"
        + "ROS fake/UNIT tests never imply base odometry stop, ROS bag or E-Stop.\n",
        encoding="utf-8",
    )
    _combined_junit(result_dir, stage_results)
    _evidence_index(result_dir)
    return code, result_dir


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--profile", choices=("unit", "ros-fake", "gazebo-e2e"),
                   default="unit")
    p.add_argument("--all", action="store_true", help="run all P1 gates for the chosen profile")
    p.add_argument("--repeat", type=int, default=1)
    p.add_argument("--timeout-sec", type=float, default=120)
    p.add_argument("--results-root", type=Path, default=Path("results/p1"))
    p.add_argument("--allow-partial-ci", action="store_true",
                   help="CI collection returns 0 when PARTIAL_VERIFIED; never accepts gates")
    args = p.parse_args(argv)
    try:
        code, directory = run(
            args.profile, repeat=args.repeat, timeout_sec=args.timeout_sec,
            results_root=args.results_root, allow_partial_ci=args.allow_partial_ci,
        )
        print(json.dumps({"run_dir": str(directory), "exit_code": code,
                          "gate_accepted": False, "profile": args.profile}))
        return code
    except (ValueError, OSError, subprocess.SubprocessError) as exc:
        print("RUNNER_ERROR: " + type(exc).__name__ + ": " + str(exc),
              file=sys.stderr)
        return EXIT_ERROR


if __name__ == "__main__":
    raise SystemExit(main())
