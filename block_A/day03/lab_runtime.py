"""D03 complete teaching harness; the ONLY mandatory TODOs are the two mappers.

Pure Python, synthetic fixtures, no live robot, no ROS control messages.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from p1_adapter_todo import diagnose_p1_state
from todo_safety import DiagnosticSample, assess_diagnostic

HERE = Path(__file__).resolve().parent
FIXTURE = HERE / 'p1_states.jsonl'


def load_cases(path: Path = FIXTURE) -> list[dict[str, Any]]:
    if not path.is_file():
        raise ValueError(f'fixture missing: {path}')
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for number, line in enumerate(path.read_text(encoding='utf-8').splitlines(), 1):
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except ValueError as exc:
            raise ValueError(f'fixture line {number}: invalid JSON') from exc
        if (not isinstance(item, dict) or not isinstance(item.get('case_id'), str)
                or item['case_id'] in seen or not isinstance(item.get('payload'), dict)
                or type(item.get('expected_level')) is not int
                or not isinstance(item.get('expected_message'), str)
                or type(item.get('received_mono')) not in (int, float)
                or type(item.get('now_mono')) not in (int, float)):
            raise ValueError(f'fixture line {number}: malformed contract or duplicated case')
        seen.add(item['case_id'])
        result.append(item)
    if not result:
        raise ValueError('fixture is empty')
    return result


def inspect_cases(path: Path = FIXTURE) -> int:
    print('D03 P1 synthetic fixture inspection | read-only | no ROS/Gazebo')
    print('case_id                  state                  expected_level  expected_message')
    for c in load_cases(path):
        state = c['payload'].get('state', '(absent)')
        print(f"{c['case_id']:<24} {state:<22} {c['expected_level']:<15} {c['expected_message']}")
    print('INSPECT_OK | actual student TODO execution: NOT_RUN')
    return 0


def run_cases(path: Path = FIXTURE) -> int:
    cases = load_cases(path)
    failures = 0
    for c in cases:
        name = c['case_id']
        raw = json.dumps(c['payload'], ensure_ascii=False)
        try:
            record = diagnose_p1_state(raw, received_mono=c['received_mono'],
                                       now_mono=c['now_mono'])
            actual = (record.level, record.message)
            expected = (c['expected_level'], c['expected_message'])
            ok = actual == expected
            if not ok:
                failures += 1
            print(f"[{('PASS' if ok else 'FAIL')}] {name} | expected={expected} actual={actual}")
            # The downstream policy is also exercised without ever acting on a robot.
            verdict = assess_diagnostic(
                DiagnosticSample(record.level, record.name, c['received_mono'], record.message),
                now_mono=c['now_mono'], timeout_s=0.5,
                sw_stop_latched=(c['payload'].get('state') == 'SW_STOP_LATCHED'),
                prior_protective_stop=(c['payload'].get('state') == 'RECOVERY_REQUIRED'),
            )
            print(f'       Safe Mode candidate={verdict.mode} (NOT motion authorization)')
        except Exception as exc:
            failures += 1
            # Never print raw payload, goal UUID, credential or other private fields.
            print(f'[FAIL] {name} | adapter raised {type(exc).__name__}')
    print(f'D03_REPLAY_RESULT cases={len(cases)} failures={failures} '
          'ROS_VERIFIED=NOT_RUN GAZEBO_VERIFIED=NOT_RUN')
    return 0 if failures == 0 else 3


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='AXIA D03 offline P1 diagnostic lab')
    parser.add_argument('mode', choices=('inspect', 'run'))
    args = parser.parse_args(argv)
    try:
        return inspect_cases() if args.mode == 'inspect' else run_cases()
    except ValueError as exc:
        print(f'BLOCKED: {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())