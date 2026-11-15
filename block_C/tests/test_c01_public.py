"""C-01 acceptance: deterministic source, integrity, split/quality semantics (Python L0)."""
import csv
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
FIX = ROOT / 'fixtures'
sys.path.insert(0, str(FIX))

EXPECTED = {'generator.py', 'normal_train.csv', 'normal_valid.csv', 'test_mixed.csv',
            'schema.json', 'scenario_manifest.json', 'PROVENANCE.md'}


def generated(tmp_path):
    from generator import write_fixture
    write_fixture(tmp_path)
    return tmp_path


def rows(path):
    with path.open(newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def test_c01_t01_determinism(tmp_path):
    one = generated(tmp_path / 'one')
    two = generated(tmp_path / 'two')
    assert {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in one.iterdir()} == {
        p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in two.iterdir()}
    assert {p.name for p in one.iterdir()} == EXPECTED | {'SHA256SUMS'}


def test_c01_t02_strict_checksum_and_tamper(tmp_path):
    from generator import check_fixture
    original = generated(tmp_path / 'ok')
    assert check_fixture(original)['rows'] == 4599
    (original / 'normal_train.csv').write_bytes((original / 'normal_train.csv').read_bytes() + b'x')
    with pytest.raises(ValueError, match='hash mismatch'):
        check_fixture(original)
    other = generated(tmp_path / 'bad')
    (other / 'SHA256SUMS').write_text((other / 'SHA256SUMS').read_text() + '0'*64 + '  ../../escape\n')
    with pytest.raises(ValueError, match='checksum inventory'):
        check_fixture(other)


def test_c01_t03_schema_and_units(tmp_path):
    from generator import check_fixture, COLUMNS
    target = generated(tmp_path / 'ok')
    schema = json.loads((target / 'schema.json').read_text())
    assert schema['columns'] == list(COLUMNS)
    assert schema['sample_hz'] == 10
    assert schema['step_ns'] == 100_000_000
    assert schema['time_domain'] == 'SYNTHETIC_TRACE_LOCAL_NS'
    assert schema['units'] == {'current_a': 'A', 'torque_nm': 'N*m', 'accel_mps2': 'm/s^2'}
    assert check_fixture(target)['traces'] == 46


def test_c01_t04_split_disjoint_and_counts(tmp_path):
    from generator import check_fixture
    target = generated(tmp_path / 'ok')
    cases = [rows(target / n) for n in ('normal_train.csv', 'normal_valid.csv', 'test_mixed.csv')]
    assert list(map(len, cases)) == [2400, 800, 1399]
    tids = [set(r['trace_id'] for r in c) for c in cases]
    assert [len(s) for s in tids] == [24, 8, 14]
    assert not tids[0] & tids[1] and not tids[0] & tids[2] and not tids[1] & tids[2]
    assert check_fixture(target)['rows'] == 4599


def test_c01_t05_labels_and_anomaly_inventory(tmp_path):
    target = generated(tmp_path / 'ok')
    train, valid, test = [rows(target / n) for n in ('normal_train.csv', 'normal_valid.csv', 'test_mixed.csv')]
    assert {r['truth_label'] for r in train + valid} == {'0'}
    manifest = json.loads((target / 'scenario_manifest.json').read_text())
    assert manifest['trace_class_counts'] == {'normal_test': 4, 'anomaly_test': 6, 'quality_test': 4}
    assert sorted(manifest['anomaly_cases'].values()) == sorted(['CURRENT_SPIKE']*2 + ['TORQUE_DRIFT']*2 + ['ACCEL_VIBRATION']*2)
    assert {-1, 0, 1} == {int(r['truth_label']) for r in test}


def test_c01_t06_quality_cases_and_train_rejection(tmp_path):
    from generator import check_fixture, validate_trace_rows
    target = generated(tmp_path / 'ok')
    test = rows(target / 'test_mixed.csv')
    cases = json.loads((target / 'scenario_manifest.json').read_text())['quality_cases']
    assert set(cases.values()) == {'MISSING_VALUE', 'SAMPLE_GAP', 'STAMP_REGRESSION', 'TIMESTAMP_DRIFT'}
    for trace_id, reason in cases.items():
        trace = [r for r in test if r['trace_id'] == trace_id]
        assert {r['truth_label'] for r in trace} == {'-1'}
        assert validate_trace_rows(trace, allow_quality=True) == reason
        with pytest.raises(ValueError):
            validate_trace_rows(trace, allow_quality=False)
    assert check_fixture(target)['quality_traces'] == 4


def test_c01_t07_readonly_check_and_no_overwrite(tmp_path):
    from generator import write_fixture, check_fixture
    target = generated(tmp_path / 'ok')
    before = {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in target.iterdir()}
    assert check_fixture(target)['traces'] == 46
    assert {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in target.iterdir()} == before
    with pytest.raises(FileExistsError):
        write_fixture(target)


def test_c01_t08_no_ros_control_and_no_private_leak():
    script = (FIX / 'generator.py').read_text()
    for prohibited in ('import rclpy', 'NavigateToPose', '/cmd_vel', 'SafetySupervisor'):
        assert prohibited not in script
    assert not any((FIX / name).exists() for name in ('hidden_tests', 'SOLUTION.py', '.env'))
    assert 'SYNTHETIC_COURSE_FIXTURE' in script


def test_c01_t02_pycache_is_not_part_of_fixture_inventory(tmp_path):
    from generator import check_fixture
    target = generated(tmp_path / 'ok')
    cache = target / '__pycache__'
    cache.mkdir()
    (cache / 'generator.pyc').write_bytes(b'ignored local bytecode cache')
    assert check_fixture(target)['traces'] == 46
