"""Isolated real-pytest subprocess runner for ROS fake integration cases.

No fabricated PASS. Every discovered top-level test uses a fresh Python
process, ROS context, localhost-only DDS domain, and independent JUnit.
"""
import ast
import fcntl
import os
from pathlib import Path
import random
import signal
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET


def list_explicit_test_cases(paths, *, root: Path) -> list[str]:
    root=Path(root).resolve()
    found=[]
    for file in paths:
        file=Path(file).resolve()
        if not file.is_file() or not file.is_relative_to(root):
            raise ValueError("unsafe or missing ROS test path")
        module=ast.parse(file.read_text(encoding="utf-8"),filename=str(file))
        for node in module.body:
            if isinstance(node,ast.ClassDef):
                if any(isinstance(child,(ast.FunctionDef,ast.AsyncFunctionDef))
                       and child.name.startswith("test_") for child in node.body):
                    raise ValueError("test class unsupported; isolate explicitly")
            if not isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)):
                continue
            if not node.name.startswith("test_"):
                continue
            for decorator in node.decorator_list:
                if "parametrize" in ast.unparse(decorator):
                    raise ValueError("parametrize requires explicit case ids")
            found.append(file.relative_to(root).as_posix()+"::"+node.name)
    if not found or len(set(found)) != len(found):
        raise ValueError("empty or duplicate ROS test case IDs")
    return found


# 60..100 is inside the ROS 2 Linux default recommended 0..101 range.
# The old 191..231 pool included 191..214, whose DDS UDP ports overlap
# Linux ephemeral ports; potential discovery instability in isolated tests.
# Keep 41 choices for 36 distinct fake-ROS test cases across 3 repeats.
SAFE_ROS_DOMAIN_IDS = tuple(range(60, 101))


def _acquire_domain(used_domains: set[int]):
    # fcntl is advisory: other ROS applications must still be isolated.
    lock_root=Path(tempfile.gettempdir())/"axia_p1_ros_domain_locks"
    lock_root.mkdir(mode=0o700,exist_ok=True)
    candidates=list(SAFE_ROS_DOMAIN_IDS)
    random.SystemRandom().shuffle(candidates)
    for domain in candidates:
        if domain in used_domains:
            continue
        fd=os.open(str(lock_root / ("domain_%03d.lock" % domain)),
                   os.O_CREAT|os.O_RDWR,0o600)
        try:
            fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:
            os.close(fd)
            continue
        used_domains.add(domain)
        return domain,fd
    raise RuntimeError("no unused DDS domain in 60..100; fail closed")


def _stop_process(proc):
    if proc.poll() is not None:
        return
    try:
        os.killpg(proc.pid,signal.SIGTERM)
        proc.wait(timeout=3)
    except (ProcessLookupError,subprocess.TimeoutExpired):
        if proc.poll() is None:
            os.killpg(proc.pid,signal.SIGKILL)
            proc.wait(timeout=3)


def _classify_single_case(path: Path, test_id: str, returncode: int) -> str:
    if not path.is_file() or returncode != 0:
        return "FAIL"
    try:
        root=ET.parse(path).getroot()
        cases=list(root.iter("testcase"))
    except (ET.ParseError, OSError):
        return "FAIL"
    expected=test_id.rsplit("::",1)[-1]
    if len(cases)!=1 or cases[0].attrib.get("name")!=expected:
        return "FAIL"
    if any(child.tag in ("skipped","error","failure") for child in cases[0]):
        return "FAIL"
    return "PASS"


def run_isolated_ros_cases(paths, *, dest: Path, root: Path,
                           timeout_sec: float, env: dict,
                           used_domains: set[int]) -> dict:
    """Run and aggregate all explicit top-level tests (no skip/retry allowed)."""
    root=Path(root).resolve()
    dest=Path(dest)
    dest.mkdir(parents=True,exist_ok=True)
    cases=list_explicit_test_cases(paths,root=root)
    aggregated=ET.Element("testsuites")
    outcome=[]
    for i,case_id in enumerate(cases,1):
        case_dir=dest/"cases"/("case_%02d" % i)
        case_dir.mkdir(parents=True,exist_ok=False)
        domain,fd=_acquire_domain(used_domains)
        child_env=dict(env)
        child_env["ROS_DOMAIN_ID"]=str(domain)
        child_env.pop("ROS_LOCALHOST_ONLY",None)
        child_env.pop("ROS_STATIC_PEERS",None)
        child_env["ROS_AUTOMATIC_DISCOVERY_RANGE"]="LOCALHOST"
        junit=case_dir/"pytest.xml"
        cmd=[sys.executable,"-m","pytest","-q","-ra",case_id,
             "--junitxml="+str(junit)]
        timed_out=False
        rc=4
        pid=None
        start=time.monotonic_ns()
        try:
            with (case_dir/"stdout.log").open("w",encoding="utf-8") as out, (
                case_dir/"stderr.log").open("w",encoding="utf-8") as err:
                proc=subprocess.Popen(cmd,cwd=root,env=child_env,
                                      stdout=out,stderr=err,
                                      start_new_session=True)
                pid=proc.pid
                try:
                    rc=proc.wait(timeout=timeout_sec)
                except subprocess.TimeoutExpired:
                    timed_out=True
                    _stop_process(proc)
                    rc=124
                finally:
                    _stop_process(proc)
        except (OSError,ValueError) as exc:
            (case_dir/"runner_error.txt").write_text(
                type(exc).__name__+": "+str(exc),encoding="utf-8")
        finally:
            fcntl.flock(fd,fcntl.LOCK_UN)
            os.close(fd)
        status=_classify_single_case(junit,case_id,rc)
        if status=="PASS":
            # Keep original pytest testcase and real event timestamps.
            tree=ET.parse(junit).getroot()
            for suite in tree.iter("testsuite"):
                if not any(ch.tag=="testsuite" for ch in suite):
                    aggregated.append(suite)
        else:
            suite=ET.SubElement(aggregated,"testsuite",tests="1",
                                failures="1",name=case_id)
            node=ET.SubElement(suite,"testcase",name=case_id.rsplit("::",1)[-1])
            ET.SubElement(node,"failure",message="REAL_CASE_FAILED_OR_MISSING",
                          type="RunnerFailure").text=(
                f"rc={rc}; elapsed_ns={time.monotonic_ns()-start}; "
                f"junit={junit}; stderr={case_dir/'stderr.log'}"
            )
        outcome.append({
            "test_id":case_id,"status":status,"domain_id":domain,
            "pid":pid,"returncode":rc,"timed_out":timed_out,
            "elapsed_steady_ns":time.monotonic_ns()-start,
            "junit_file":str(junit.relative_to(dest)),
        })
    ET.ElementTree(aggregated).write(dest/"pytest.xml",encoding="utf-8",
                                     xml_declaration=True)
    stage_status="PASS" if all(item["status"]=="PASS" for item in outcome) else "FAIL"
    # Preserve normal stage diagnostics expected by the original runner.
    with (dest/"stdout.log").open("w",encoding="utf-8") as output:
        for item in outcome:
            output.write(f"{item['test_id']} status={item['status']} "
                         f"domain={item['domain_id']} rc={item['returncode']}\n")
    (dest/"stderr.log").write_text(
        "Case stdout/stderr: cases/case_NN/{stdout,stderr}.log\n",
        encoding="utf-8"
    )
    return {
        "status":stage_status,"returncode":0 if stage_status=="PASS" else 1,
        "timed_out":any(item["timed_out"] for item in outcome),
        "cases":outcome,
    }
