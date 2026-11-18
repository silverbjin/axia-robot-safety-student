"""Non-TODO execution harness tests: must PASS before students implement mappers."""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DAY03 = ROOT / 'block_A/day03'
sys.path.insert(0, str(DAY03))
from lab_runtime import load_cases, inspect_cases


def test_synthetic_fixture_parse_and_unique_ids():
    cases = load_cases()
    assert len(cases) == 9
    assert len({c['case_id'] for c in cases}) == len(cases)


def test_fixture_inspect_no_student_impl_needed(capsys):
    assert inspect_cases() == 0
    data = capsys.readouterr().out
    assert 'INSPECT_OK' in data and 'SCAN_DROPPED' in data
    assert 'NOT_RUN' in data


def test_fixture_loader_rejects_duplicate_ids(tmp_path):
    fixture = tmp_path / 'bad.jsonl'
    item = load_cases()[0]
    fixture.write_text(json.dumps(item) + '\n' + json.dumps(item), encoding='utf-8')
    try:
        load_cases(fixture)
    except ValueError as exc:
        assert 'duplicated' in str(exc)
    else:
        raise AssertionError('duplicate ID accepted')


def test_fixture_run_blocks_unfinished_mapper_without_secret_leak():
    # Template has a placeholder; inspection remains operational, execution
    # fails closed until TODO is implemented. Do not print goal_id from fixtures.
    p = subprocess.run([sys.executable, str(DAY03 / 'lab_runtime.py'), 'inspect'],
                       capture_output=True, text=True, check=False)
    assert p.returncode == 0
    assert 'PRIVATE_SYNTHETIC_GOAL' not in p.stdout


def test_ros_bridge_has_no_motion_commands():
    code = (DAY03 / 'ros_diagnostics_bridge.py').read_text()
    assert '"/diagnostics"' in code
    assert '"/axia/safety/state"' in code
    assert '"/cmd_vel"' not in code
    assert '"/navigate_to_pose"' not in code