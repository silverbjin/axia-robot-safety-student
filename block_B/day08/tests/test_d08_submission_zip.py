"""D08 public ZIP contract: green independently of intentionally RED TODO."""
import csv
import hashlib
import io
import json
import zipfile
from pathlib import Path
from block_B.day08.submission_zip import package_submission

IDS=("clear_replan","slow","stop","lost","stale_depth","stale_track")
FLAGS=("ros_verified","gazebo_verified","robot_moved",
       "collision_free_verified","control_published","safety_certified")
def make_run(root):
    run=root/"case_output"
    run.mkdir()
    results=[{
      "case_id":id,"source":"D08_SYNTHETIC_CLASSROOM",
      "verified_level":"PYTHON_ONLY",
      "range_status":("UNKNOWN" if id in ("lost","stale_depth","stale_track") else "CLEAR"),
      "advice":("UNKNOWN_REVIEW" if id in ("lost","stale_depth","stale_track") else "REPLAN_REVIEW"),
      **{k:False for k in FLAGS}
    } for id in IDS]
    data={"schema":"axia.d08.report.v1","status":"D08_EDU_PYTHON_L0_COMPLETE",
      "source":"D08_SYNTHETIC_CLASSROOM","verified_level":"PYTHON_ONLY",
      "fixture_sha256":"a"*64,"case_count":6,"results":results,
      **{k:False for k in FLAGS}}
    (run/"summary.json").write_text(json.dumps(data)+"\n")
    with (run/"trace.csv").open("w",newline="") as f:
        w=csv.writer(f);w.writerow(("case_id","advice"))
        w.writerows([(id,results[i]["advice"]) for i,id in enumerate(IDS)])
    (run/"pytest.txt").write_text("6 passed in 0.02s\n")
    return run

def test_zip_exact_files_and_sha256_manifest(tmp_path):
    run=make_run(tmp_path)
    out=tmp_path/"d08_submission.zip"
    assert package_submission(run,out)==0
    with zipfile.ZipFile(out) as z:
        assert sorted(z.namelist())==sorted(["trace.csv","summary.json","pytest.txt","SHA256SUMS"])
        assert z.testzip() is None
        for line in z.read("SHA256SUMS").decode().splitlines():
            digest,filename=line.split("  ")
            assert hashlib.sha256(z.read(filename)).hexdigest()==digest
    assert package_submission(run,out)==2

def test_zip_forged_real_world_claim_is_blocked(tmp_path):
    run=make_run(tmp_path)
    p=run/"summary.json"
    v=json.loads(p.read_text())
    v["gazebo_verified"]=True
    p.write_text(json.dumps(v))
    out=tmp_path/"x.zip"
    assert package_submission(run,out)==2
    assert not out.exists()

def test_zip_forged_case_level_motion_is_blocked(tmp_path):
    run=make_run(tmp_path)
    p=run/"summary.json"
    v=json.loads(p.read_text())
    v["results"][0]["robot_moved"]=True
    p.write_text(json.dumps(v))
    out=tmp_path/"x.zip"
    assert package_submission(run,out)==2
    assert not out.exists()

def test_zip_rejects_symlink_or_mismatched_trace(tmp_path):
    run=make_run(tmp_path)
    (run/"pytest.txt").unlink()
    (run/"pytest.txt").symlink_to(run/"summary.json")
    assert package_submission(run,tmp_path/"first.zip")==2
    (run/"pytest.txt").unlink()
    (run/"pytest.txt").write_text("6 passed in 0.02s\n")
    (run/"trace.csv").write_text("case_id\nunknown\n")
    assert package_submission(run,tmp_path/"second.zip")==2

def test_zip_requires_pytest_pass_not_hidden_failure(tmp_path):
    run=make_run(tmp_path)
    (run/"pytest.txt").write_text("1 failed, 5 passed in 0.02s\n")
    assert package_submission(run,tmp_path/"failure.zip")==2

def test_student_source_never_implements_ros_safety_controller():
    root=Path(__file__).resolve().parents[1]
    for path in ("integration_todo.py","run_lab.py","submission_zip.py"):
        code=(root/path).read_text()
        for token in ("import rclpy","ActionClient(","NavigateToPose(", "create_publisher(",
                      "gz service","publish(Twist","os.system("):
            assert token not in code

def test_partial_zip_write_failure_leaves_no_success_looking_file(tmp_path,monkeypatch):
    import zipfile
    run=make_run(tmp_path)
    out=tmp_path/"partial.zip"
    real_zipfile=zipfile.ZipFile
    class DiskFailureZip(real_zipfile):
        def writestr(self,*args,**kwargs):
            raise OSError("simulated disk full during first ZIP entry")
    monkeypatch.setattr(zipfile,"ZipFile",DiskFailureZip)
    assert package_submission(run,out)==2
    assert not out.exists()
