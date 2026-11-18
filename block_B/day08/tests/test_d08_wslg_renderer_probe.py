"""Deterministic WSLg GPU path L0 contract; never a Gazebo performance claim."""
from pathlib import Path
import importlib.util
import subprocess
import sys

SCRIPT=Path(__file__).resolve().parents[1]/"tools/d08_wslg_renderer_probe.py"

def _module():
    spec=importlib.util.spec_from_file_location("d08_gl_probe",SCRIPT)
    module=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=module
    spec.loader.exec_module(module)
    return module

def test_gl_probe_classifies_real_wslg_fallback_safely():
    mod=_module()
    assert mod.classify({
      "default":"llvmpipe (LLVM 17.0.6)",
      "d3d12_auto":"D3D12 (Intel Arc)",
      "d3d12_nvidia":"llvmpipe (LLVM 17.0.6)"
    })=="NVIDIA_SELECTION_LLVMPIPE_FALLBACK_CANDIDATE"
    assert mod.classify({
      "default":"llvmpipe (LLVM 20)", "d3d12_auto":"D3D12 (Intel)"
    })=="DEFAULT_SOFTWARE_FALLBACK_D3D12_AVAILABLE"
    assert mod.classify({"default":"D3D12 (NVIDIA)"})=="D3D12_AVAILABLE_RTF_NOT_VERIFIED"
    assert mod.classify({})=="RENDERER_NOT_MEASURED"

def test_renderer_gpu_child_env_is_not_global_or_goal_controller():
    mod=_module()
    for env_name in mod.BACKENDS:
        e=mod.environment(env_name)
        if env_name=="d3d12_nvidia":
            assert e["GALLIUM_DRIVER"]=="d3d12"
            assert e["MESA_D3D12_DEFAULT_ADAPTER_NAME"]=="NVIDIA"
        elif env_name=="default":
            assert "GALLIUM_DRIVER" not in e
            assert "MESA_D3D12_DEFAULT_ADAPTER_NAME" not in e
    s=SCRIPT.read_text()
    for banned in ("sudo ", "apt install", "ros2 topic pub", "gz service -s",
                   "send_goal(", "cmd_vel pub", "wsl --shutdown", "rm -rf"):
        assert banned not in s

def test_offline_static_self_check():
    p=subprocess.run([sys.executable,str(SCRIPT),"--self-check"],
                     capture_output=True,text=True,timeout=15)
    assert p.returncode==0,p.stderr
    assert "D08_GL_PROBE_STATIC_PASS ROS_NOT_RUN GAZEBO_NOT_RUN" in p.stdout
