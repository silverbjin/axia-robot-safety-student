"""Optional challenge grading only: excluded from mandatory 30-test GREEN CI."""
import json

from challenges import challenge1_failed_health, challenge2_recovery_sequence
from todo_safety import DiagnosticSample


def test_application_01_prioritize_explicit_failed_signals():
    p = {'health_diagnostics': {'clock_ok': True, 'scan_ok': False,
         'cm_lifecycle_ok': None, 'nav2_action_ready': False}}
    assert challenge1_failed_health(json.dumps(p)) == ('scan_ok', 'nav2_action_ready')


def test_application_01_all_healthy():
    p = {'health_diagnostics': {'clock_ok': True, 'scan_ok': True}}
    assert challenge1_failed_health(json.dumps(p)) == ()


def test_application_02_no_automatic_rearm_after_error():
    samples = [DiagnosticSample(2, 'scan', 10.), DiagnosticSample(0, 'scan', 11.),
               DiagnosticSample(0, 'scan', 12.)]
    modes = [x.mode for x in challenge2_recovery_sequence(samples)]
    assert modes == ['PROTECTIVE_STOP', 'RECOVERY_REQUIRED', 'RECOVERY_REQUIRED']


def test_application_02_warning_without_prior_fault():
    samples = [DiagnosticSample(1, 'scan', 10.), DiagnosticSample(0, 'scan', 11.)]
    modes = [x.mode for x in challenge2_recovery_sequence(samples)]
    assert modes == ['LIMITED_CANDIDATE', 'NORMAL_CANDIDATE']