#!/usr/bin/env python3
"""Read-only WSLg / Mesa OpenGL renderer comparison for D08 Gazebo Ogre2.

Compares environment-only glxinfo -B child processes. DOES NOT change
Gazebo's current environment, GPU driver, .bashrc, Windows or Mesa.
Results are candidates, not proof of Gazebo-server renderer or improved RTF.
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import zipfile

RENDERER = re.compile(r"(?im)^\s*OpenGL renderer string:\s*(.+?)\s*$")
GLVERSION = re.compile(r"(?im)^\s*OpenGL core profile version string:\s*(.+?)\s*$")
BACKENDS = ("inherited", "default", "d3d12_auto", "d3d12_nvidia")

def classify(renderers: dict) -> str:
    """Pure logic: distinguishes driver fallback from expensive D3D12 rendering."""
    def norm(name):
        return str(renderers.get(name) or "").lower()
    auto=norm("d3d12_auto")
    nvidia=norm("d3d12_nvidia")
    base=norm("default")
    if ("d3d12" in auto and "llvmpipe" in nvidia):
        return "NVIDIA_SELECTION_LLVMPIPE_FALLBACK_CANDIDATE"
    if ("llvmpipe" in base and "d3d12" in auto):
        return "DEFAULT_SOFTWARE_FALLBACK_D3D12_AVAILABLE"
    if ("d3d12" in base or "d3d12" in auto or "d3d12" in nvidia):
        return "D3D12_AVAILABLE_RTF_NOT_VERIFIED"
    if any("llvmpipe" in norm(x) or "softpipe" in norm(x) for x in BACKENDS):
        return "SOFTWARE_RENDERER_ONLY"
    return "RENDERER_NOT_MEASURED"

def environment(name: str) -> dict:
    env=os.environ.copy()
    if name == "inherited":
        return env
    for key in ("GALLIUM_DRIVER","MESA_D3D12_DEFAULT_ADAPTER_NAME","LIBGL_ALWAYS_SOFTWARE"):
        env.pop(key,None)
    if name in ("d3d12_auto","d3d12_nvidia"):
        env["GALLIUM_DRIVER"]="d3d12"
    if name == "d3d12_nvidia":
        env["MESA_D3D12_DEFAULT_ADAPTER_NAME"]="NVIDIA"
    return env

def probe(name: str) -> tuple[dict,str]:
    try:
        proc=subprocess.run(["glxinfo","-B"],env=environment(name),text=True,
                            stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
                            check=False,timeout=12)
        raw=proc.stdout[-50000:]
        render=RENDERER.search(raw)
        ver=GLVERSION.search(raw)
        return {"rc":proc.returncode,"renderer":render.group(1).strip() if render else None,
                "glversion":ver.group(1).strip() if ver else None}, raw
    except (FileNotFoundError,subprocess.TimeoutExpired,OSError) as exc:
        return {"rc":127,"renderer":None,"error":str(exc)},str(exc)

def run(out: Path) -> int:
    if out.exists():
        print("D08_GL_PROBE_OUTPUT_EXISTS_NO_OVERWRITE",file=sys.stderr)
        return 2
    out.mkdir(parents=True,mode=0o700)
    records={}
    for name in BACKENDS:
        item,raw=probe(name)
        records[name]=item
        (out/f"glxinfo_{name}.txt").write_text(raw,encoding="utf-8")
    category=classify({k:v["renderer"] for k,v in records.items()})
    summary={
      "schema":"axia.d08.wslg_gl_probe.v1",
      "collected_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
      "classification":category,"probes":records,
      "scope":"READ_ONLY_GLXINFO_CHILD_PROCESSES",
      "gazebo_server_actual_renderer_verified":False,
      "actual_rtf_improved":False,
      "gpu_hardware_proven_for_gazebo":False,
      "no_goal":True,"safety_ttl_verified":False,
    }
    (out/"summary.json").write_text(json.dumps(summary,indent=2,ensure_ascii=False)+"\n")
    report=[
      "# AXIA D08 WSLg OpenGL path preflight","",
      "Classification: "+category,
      "WARNING: glxinfo child process != actual Gazebo server renderer.",
      "Compare with Gazebo ogre2.log and measured real time factor before any optimization claim.","",
    ]
    for name in BACKENDS:
        report.append(f"- {name}: {records[name]['renderer'] or 'NOT_MEASURED'}")
    (out/"REPORT.md").write_text("\n".join(report)+"\n")
    archive=out/"d08_wslg_renderer_probe.zip"
    with zipfile.ZipFile(archive,"w",compression=zipfile.ZIP_DEFLATED) as z:
        for file in out.glob("*"):
            if file.is_file() and file!=archive:
                z.write(file,arcname=file.name)
    print("D08_GL_RENDERER_CLASSIFICATION="+category)
    for name in BACKENDS:
        print("D08_GL_RENDERER_"+name.upper()+"="+(records[name]["renderer"] or "NOT_MEASURED"))
    print("D08_GL_RENDERER_GAZEBO_SERVER=NOT_VERIFIED")
    print("D08_GL_PROBE_ZIP="+str(archive))
    return 0 if any(v.get("renderer") for v in records.values()) else 3

def main()->int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out",type=Path)
    p.add_argument("--self-check",action="store_true")
    args=p.parse_args()
    if args.self_check:
        assert classify({"default":"llvmpipe","d3d12_auto":"D3D12 (Intel)","d3d12_nvidia":"llvmpipe"})=="NVIDIA_SELECTION_LLVMPIPE_FALLBACK_CANDIDATE"
        print("D08_GL_PROBE_STATIC_PASS ROS_NOT_RUN GAZEBO_NOT_RUN")
        return 0
    label=datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out=args.out.expanduser() if args.out else Path.home()/"axia_d08_diagnostics"/f"gl_{label}_{os.getpid()}"
    return run(out)

if __name__=="__main__":
    raise SystemExit(main())
