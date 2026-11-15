#!/usr/bin/env python3
"""AXIA C-01 deterministic synthetic fixture, never a real Waffle measurement.

No ROS/Gazebo or third-party dependencies. All signals use integer micro-units;
output decimal text is therefore byte-for-byte deterministic across platforms.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import hmac
import io
import json
import math
import re
from pathlib import Path

SOURCE = 'SYNTHETIC_COURSE_FIXTURE'
SEED = 2409
STEP_NS = 100_000_000
COLUMNS = ('trace_id', 'sample_idx', 'timestamp_ns', 'current_a', 'torque_nm', 'accel_mps2', 'truth_label')
FILES = ('generator.py', 'normal_train.csv', 'normal_valid.csv', 'test_mixed.csv',
         'schema.json', 'scenario_manifest.json', 'PROVENANCE.md')
ANOMALIES = ('CURRENT_SPIKE', 'CURRENT_SPIKE', 'TORQUE_DRIFT', 'TORQUE_DRIFT',
             'ACCEL_VIBRATION', 'ACCEL_VIBRATION')
QUALITY = ('MISSING_VALUE', 'SAMPLE_GAP', 'STAMP_REGRESSION', 'TIMESTAMP_DRIFT')
PROVENANCE = ("# AXIA C-01 synthetic data provenance\n\n"
              "Source: SYNTHETIC_COURSE_FIXTURE, generated deterministically by generator.py.\n"
              "Seed: 2409; sampling: synthetic 10 Hz, trace-local elapsed nanoseconds.\n"
              "License: CC0-1.0 for original AXIA synthetic tabular data and metadata.\n"
              "Signals are invented educational values, NOT real TurtleBot3 Waffle current, torque, or IMU readings.\n"
              "SHA256 checks integrity, NOT authenticity, provenance certification, or robot safety.\n"
              "Training and validation contain only label 0; holdout includes anomaly and quality traces.\n")


def _json_bytes(obj):
    return (json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=True) + '\n').encode('utf-8')


def _signal_text(micro):
    return ('-' if micro < 0 else '') + f'{abs(micro) // 1_000_000}.{abs(micro) % 1_000_000:06d}'


def _trace_rows(trace_id, trace_number, kind=None):
    result = []
    for i in range(100):
        if kind == 'SAMPLE_GAP' and i == 55:
            continue
        timestamp = i * (102_000_000 if kind == 'TIMESTAMP_DRIFT' else STEP_NS)
        if kind == 'STAMP_REGRESSION' and i == 50:
            timestamp = 48 * STEP_NS
        current = 2_000_000 + (i % 20) * 15_000 + ((SEED + trace_number * 13 + i * 7) % 19 - 9) * 6_000
        torque = 400_000 + (i % 15) * 4_000 + ((SEED + trace_number * 11 + i * 5) % 13 - 6) * 2_000
        accel = 100_000 + (i % 30 - 15) * 7_000 + ((SEED + trace_number * 17 + i * 3) % 11 - 5) * 8_000
        active = kind in ANOMALIES and 40 <= i < 70
        if active and kind == 'CURRENT_SPIKE':
            current += 3_000_000
        elif active and kind == 'TORQUE_DRIFT':
            torque += (i - 39) * 25_000
        elif active and kind == 'ACCEL_VIBRATION':
            accel += 900_000 if i % 2 else -900_000
        label = -1 if kind in QUALITY else (1 if active else 0)
        result.append([trace_id, str(i), str(timestamp), _signal_text(current),
                       '' if kind == 'MISSING_VALUE' and i == 55 else _signal_text(torque),
                       _signal_text(accel), str(label)])
    return result


def _csv_bytes(traces):
    # No CSV field contains commas or quotes: deterministic LF across Linux/Windows.
    lines = [','.join(COLUMNS)]
    for trace_id, trace_number, kind in traces:
        lines.extend(','.join(row) for row in _trace_rows(trace_id, trace_number, kind))
    return ('\n'.join(lines) + '\n').encode('utf-8')


def _splits():
    train = [(f'TRN_{i:02d}', i, None) for i in range(24)]
    valid = [(f'VAL_{i:02d}', i + 24, None) for i in range(8)]
    normal = [(f'TST_N_{i:02d}', i + 32, None) for i in range(4)]
    anomaly = [(f'TST_A_{i:02d}', i + 36, kind) for i, kind in enumerate(ANOMALIES)]
    quality = [(f'TST_Q_{i:02d}', i + 42, kind) for i, kind in enumerate(QUALITY)]
    return {'normal_train.csv': train, 'normal_valid.csv': valid,
            'test_mixed.csv': normal + anomaly + quality}


def build_files():
    split = _splits()
    schema = {
        'schema_version': 1, 'source': SOURCE, 'columns': list(COLUMNS),
        'sample_hz': 10, 'step_ns': STEP_NS, 'time_domain': 'SYNTHETIC_TRACE_LOCAL_NS',
        'units': {'current_a': 'A', 'torque_nm': 'N*m', 'accel_mps2': 'm/s^2'},
        'truth_labels': {'-1': 'INSUFFICIENT_DATA', '0': 'NORMAL', '1': 'ANOMALY'},
        'data_quality_policy': 'INVALID_IS_INSUFFICIENT_DATA',
        'model_features': ['current_a', 'torque_nm', 'accel_mps2'],
    }
    manifest = {
        'schema_version': 1, 'source': SOURCE, 'seed': SEED,
        'generator_version': 'c01-v1', 'license': 'CC0-1.0',
        'normal_only_train_valid': True,
        'split_files': list(split),
        'trace_counts': {'normal_train.csv': 24, 'normal_valid.csv': 8, 'test_mixed.csv': 14},
        'trace_id_inventory': {name: [t[0] for t in traces] for name, traces in split.items()},
        'trace_class_counts': {'normal_test': 4, 'anomaly_test': 6, 'quality_test': 4},
        'anomaly_cases': {t[0]: t[2] for t in split['test_mixed.csv'] if t[2] in ANOMALIES},
        'quality_cases': {t[0]: t[2] for t in split['test_mixed.csv'] if t[2] in QUALITY},
        'expected_rows': {'normal_train.csv': 2400, 'normal_valid.csv': 800, 'test_mixed.csv': 1399},
    }
    data = {'generator.py': Path(__file__).read_bytes(), 'schema.json': _json_bytes(schema),
            'scenario_manifest.json': _json_bytes(manifest),
            'PROVENANCE.md': PROVENANCE.encode('utf-8')}
    for name, traces in split.items():
        data[name] = _csv_bytes(traces)
    return data


def _sha_manifest(data):
    return ''.join(f'{hashlib.sha256(data[name]).hexdigest()}  {name}\n' for name in sorted(FILES)).encode('ascii')


def write_fixture(folder):
    target = Path(folder)
    if target.exists():
        raise FileExistsError(f'output exists, refuse overwrite: {target}')
    target.mkdir(parents=True)
    data = build_files()
    for name in FILES:
        (target / name).write_bytes(data[name])
    (target / 'SHA256SUMS').write_bytes(_sha_manifest(data))
    return target


def validate_trace_rows(trace, *, allow_quality):
    if not trace or len({row['trace_id'] for row in trace}) != 1:
        raise ValueError('trace grouping invalid')
    indices = [int(r['sample_idx']) for r in trace]
    stamps = [int(r['timestamp_ns']) for r in trace]
    if indices[0] != 0 or any(b <= a for a, b in zip(indices, indices[1:])):
        raise ValueError('sample sequence invalid')
    if any(r['truth_label'] not in {'-1', '0', '1'} for r in trace):
        raise ValueError('truth label invalid')
    missing = any(any(r[col] == '' for col in ('current_a', 'torque_nm', 'accel_mps2')) for r in trace)
    for row in trace:
        for col in ('current_a', 'torque_nm', 'accel_mps2'):
            if row[col] != '' and not math.isfinite(float(row[col])):
                raise ValueError('nonfinite signal')
    reason = None
    if missing:
        reason = 'MISSING_VALUE'
    elif len(trace) == 99 and len(set(indices)) == 99 and indices[-1] == 99:
        reason = 'SAMPLE_GAP'
    elif any(b <= a for a, b in zip(stamps, stamps[1:])):
        reason = 'STAMP_REGRESSION'
    elif any(stamp != idx * STEP_NS for idx, stamp in zip(indices, stamps)):
        reason = 'TIMESTAMP_DRIFT'
    if not reason and (len(trace) != 100 or indices != list(range(100))):
        raise ValueError('trace indices invalid')
    if reason and not allow_quality:
        raise ValueError('quality trace not allowed in normal split: ' + reason)
    labels = {row['truth_label'] for row in trace}
    if reason and labels != {'-1'}:
        raise ValueError('quality label mismatch')
    if not reason and '-1' in labels:
        raise ValueError('unexpected quality label')
    return reason


def check_fixture(folder):
    target = Path(folder)
    if not target.is_dir() or target.is_symlink():
        raise ValueError('fixture directory unavailable')
    entries = {p.name for p in target.iterdir() if p.is_file() or p.is_symlink()}
    if entries != set(FILES) | {'SHA256SUMS'} or any(
        p.is_dir() and p.name != '__pycache__' for p in target.iterdir()
    ):
        raise ValueError('checksum inventory mismatch')
    if any((target / name).is_symlink() for name in FILES + ('SHA256SUMS',)):
        raise ValueError('symlink forbidden')
    checksums = (target / 'SHA256SUMS').read_text(encoding='ascii').splitlines()
    inventory = {}
    for line in checksums:
        match = re.fullmatch(r'([0-9a-f]{64})  ([A-Za-z0-9_.-]+)', line)
        if not match or match.group(2) in inventory:
            raise ValueError('checksum inventory malformed')
        inventory[match.group(2)] = match.group(1)
    if set(inventory) != set(FILES):
        raise ValueError('checksum inventory mismatch')
    expected = build_files()
    for name in FILES:
        actual = (target / name).read_bytes()
        digest = hashlib.sha256(actual).hexdigest()
        if not hmac.compare_digest(digest, inventory[name]):
            raise ValueError('hash mismatch: ' + name)
        if actual != expected[name]:
            raise ValueError('fixture not reproducible: ' + name)
    samples = {}
    for name in ('normal_train.csv', 'normal_valid.csv', 'test_mixed.csv'):
        with (target / name).open(newline='', encoding='utf-8') as stream:
            reader = csv.DictReader(stream)
            if reader.fieldnames != list(COLUMNS):
                raise ValueError('schema mismatch: ' + name)
            samples[name] = list(reader)
    counts = [len(samples[name]) for name in ('normal_train.csv', 'normal_valid.csv', 'test_mixed.csv')]
    if counts != [2400, 800, 1399]:
        raise ValueError('row counts mismatch')
    traces = {}
    for name, rows in samples.items():
        mapping = {}
        for row in rows:
            mapping.setdefault(row['trace_id'], []).append(row)
        traces[name] = mapping
        for trace in mapping.values():
            validate_trace_rows(trace, allow_quality=name == 'test_mixed.csv')
    keys = [set(groups) for groups in traces.values()]
    if len(keys[0]) != 24 or len(keys[1]) != 8 or len(keys[2]) != 14 or any(
        keys[i] & keys[j] for i in range(3) for j in range(i + 1, 3)
    ):
        raise ValueError('split leakage or inventory mismatch')
    if any(r['truth_label'] != '0' for name in ('normal_train.csv', 'normal_valid.csv')
           for r in samples[name]):
        raise ValueError('train/valid contamination')
    test = traces['test_mixed.csv']
    quality_expected = json.loads(expected['scenario_manifest.json'])['quality_cases']
    for tid, rows in test.items():
        observed = validate_trace_rows(rows, allow_quality=True)
        if observed != quality_expected.get(tid):
            raise ValueError('unexpected quality: ' + tid)
    return {'status': 'PASS', 'rows': sum(counts), 'traces': sum(map(len, keys)),
            'quality_traces': len(quality_expected), 'source': SOURCE, 'level': 'PYTHON_L0',
            'ros_actual': False, 'gazebo_actual': False}


def main(argv=None):
    parser = argparse.ArgumentParser()
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--write', action='store_true')
    action.add_argument('--check', action='store_true')
    parser.add_argument('--output-dir', type=Path)
    parser.add_argument('--fixture-dir', type=Path)
    args = parser.parse_args(argv)
    try:
        if args.write:
            if args.output_dir is None or args.fixture_dir is not None:
                parser.error('--write requires --output-dir only')
            write_fixture(args.output_dir)
            print('C01_GENERATED source=' + SOURCE)
        else:
            if args.fixture_dir is None or args.output_dir is not None:
                parser.error('--check requires --fixture-dir only')
            result = check_fixture(args.fixture_dir)
            print('C01_FIXTURE_CONTRACT_PASS ' + json.dumps(result, sort_keys=True))
        return 0
    except (ValueError, OSError) as exc:
        print('C01_CONTRACT_FAIL: ' + str(exc), file=__import__('sys').stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
