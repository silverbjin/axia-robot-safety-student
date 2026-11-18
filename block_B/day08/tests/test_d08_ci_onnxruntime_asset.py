"""Only the public CI ONNX Runtime vendor download boundary; no ROS/Gazebo."""
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[3]
TOOL=ROOT/"block_B/day04/gazebo_yolo/ci_onnxruntime_asset.py"
LAUNCH=ROOT/"block_B/day04/run_student_gazebo_yolo_once.sh"

def test_vendor_archive_prober_rejects_invalid_9_byte_payload(tmp_path):
    assert TOOL.is_file()
    dest=tmp_path/"onnxruntime-linux-x64-1.20.0.tgz"
    dest.write_bytes(b"Forbidden")
    proc=subprocess.run([sys.executable,str(TOOL),"--check",str(dest)],
                        text=True,capture_output=True,timeout=20)
    assert proc.returncode != 0
    assert "CI_ORT_ARCHIVE_REJECTED" in proc.stdout+proc.stderr

def test_ci_fetch_is_opt_in_and_offline_contract_verifies():
    assert TOOL.is_file()
    proc=subprocess.run([sys.executable,str(TOOL),"--self-test"],
                        text=True,capture_output=True,timeout=20)
    assert proc.returncode == 0,proc.stdout+proc.stderr
    assert "CI_ORT_OFFLINE_SELF_TEST_PASS" in proc.stdout

def test_ci_only_uses_api_asset_and_vendor_local_url_no_owner_change():
    assert TOOL.is_file()
    t=TOOL.read_text()
    s=LAUNCH.read_text()
    assert "https://api.github.com/repos/microsoft/onnxruntime/releases/tags/v1.20.0" in t
    assert "/releases/assets/" in t
    assert "application/octet-stream" in t
    assert "sha256" in t
    assert 'if [[ "$CI_HEADLESS" == 1 ]]; then' in s
    assert "ci_onnxruntime_asset.py" in s
    assert "ONNXRUNTIME_URL=file://" in s
    assert "ONNXRUNTIME_VERSION" in t
    assert "ros2 topic pub" not in t
