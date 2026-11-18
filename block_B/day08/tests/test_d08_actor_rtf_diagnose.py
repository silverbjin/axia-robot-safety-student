"""D08 Actor slowdown read-only diagnostic L0 contract (no Gazebo launched)."""
from pathlib import Path
import importlib.util
import json
import subprocess
import sys

import pytest

SCRIPT=Path(__file__).resolve().parents[1]/"tools/d08_actor_rtf_diagnose.py"

def _module():
    spec=importlib.util.spec_from_file_location("axia_d08_actor_diag",SCRIPT)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def _stats(rtf, paused=False):
    lines=[]
    for i in range(8):
        sim=i*rtf*2
        secs=int(sim)
        lines.append(f'sim_time {{\n  sec: {secs}\n  nsec: {int((sim-secs)*1e9)}\n}}\nreal_time_factor: {rtf}\npaused: {str(paused).lower()}\n---\n')
    return '\n'.join(lines)

def _scene(p):
    p.write_text('<sdf><world name="default"><actor name="axia_student_person"><script><trajectory>'
                 '<waypoint><time>0</time><pose>2.8 -0.5 1 0 0 0</pose></waypoint>'
                 '<waypoint><time>5</time><pose>2.0 -0.5 1 0 0 0</pose></waypoint>'
                 '<waypoint><time>10</time><pose>2.8 -0.5 1 0 0 0</pose></waypoint>'
                 '</trajectory></script></actor></world></sdf>',encoding="utf-8")

def test_d08_rtf_script_exists():
    assert SCRIPT.is_file()
    assert subprocess.run([sys.executable,"-m","py_compile",str(SCRIPT)],capture_output=True).returncode==0

def test_real_sdf_profile_and_low_rtf(tmp_path):
    mod=_module()
    scene=tmp_path/"scene.sdf.xacro"
    _scene(scene)
    actor=mod.actor_profile(scene)
    assert actor["segments"][0]["speed_mps_sim"]==0.16
    stats=mod.parse_stats(_stats(.25))
    result=mod.diagnosis(stats,actor)
    assert result["category"]=="LOW_RTF_CANDIDATE"
    assert actor["segments"][0]["estimated_wall_s_at_median_rtf"]==20.0
    assert result["no_goal"] and not result["safety_ttl_verified"]

def test_normal_rtf_means_slow_default_actor_not_deadlock(tmp_path):
    mod=_module()
    scene=tmp_path/"scene.sdf.xacro"
    _scene(scene)
    result=mod.diagnosis(mod.parse_stats(_stats(1.0)),mod.actor_profile(scene))
    assert result["category"]=="SLOW_ACTOR_TRAJECTORY_CANDIDATE"
    paused=mod.diagnosis(mod.parse_stats(_stats(0.0,paused=True)),mod.actor_profile(scene))
    assert paused["category"]=="SIM_PAUSED"
    missing=mod.diagnosis(mod.parse_stats("paused: false\n"),mod.actor_profile(scene))
    assert missing["category"]=="RTF_NOT_MEASURED"

def test_offline_zip_no_real_ros_claim_and_non_destructive(tmp_path):
    scene=tmp_path/"scene.sdf.xacro"
    _scene(scene)
    stats=tmp_path/"stats.txt"
    stats.write_text(_stats(.4),encoding="utf-8")
    target=tmp_path/"out"
    cmd=[sys.executable,str(SCRIPT),"--from-stats",str(stats),"--scene",str(scene),"--out",str(target)]
    first=subprocess.run(cmd,capture_output=True,text=True,timeout=20)
    assert first.returncode==0, first.stderr
    report=json.loads((target/"summary.json").read_text())
    assert report["diagnosis"]["category"]=="LOW_RTF_CANDIDATE"
    assert not report["real_ros_or_gazebo_verified_by_script"]
    assert not report["control_published"]
    assert not report["safety_ttl_verified"]
    assert (target/"d08_actor_rtf_diagnostics.zip").is_file()
    second=subprocess.run(cmd,capture_output=True,text=True,timeout=20)
    assert second.returncode==2
    assert "D08_DIAG_OUTPUT_EXISTS_NO_OVERWRITE" in second.stderr
    script=SCRIPT.read_text()
    for forbidden in ("gz service -s","ros2 topic pub","cmd_vel pub","send_goal(","rm -rf"):
        assert forbidden not in script
