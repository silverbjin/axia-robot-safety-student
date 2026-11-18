"""Block A D03 public contract: pure Python synthetic diagnostics only."""
from todo_safety import DiagnosticSample, assess_diagnostic


def test_ok_is_not_motion_authorization():
    v = assess_diagnostic(DiagnosticSample(0, "laser", 10.0), now_mono=10.2, timeout_s=0.5)
    assert (v.mode, v.reason, v.requires_manual_recovery) == ("NORMAL_CANDIDATE", "DIAGNOSTIC_OK", False)


def test_warning_requests_limited_candidate():
    v = assess_diagnostic(DiagnosticSample(1, "laser", 10.0), now_mono=10.2, timeout_s=0.5)
    assert (v.mode, v.reason) == ("LIMITED_CANDIDATE", "DIAGNOSTIC_WARN")


def test_error_fail_closed():
    v = assess_diagnostic(DiagnosticSample(2, "laser", 10.0), now_mono=10.2, timeout_s=0.5)
    assert (v.mode, v.reason, v.requires_manual_recovery) == ("PROTECTIVE_STOP", "DIAGNOSTIC_ERROR", True)


def test_level_stale_fail_closed():
    v = assess_diagnostic(DiagnosticSample(3, "laser", 10.0), now_mono=10.2, timeout_s=0.5)
    assert (v.mode, v.reason) == ("PROTECTIVE_STOP", "DIAGNOSTIC_LEVEL_STALE")


def test_transport_stale_after_timeout():
    v = assess_diagnostic(DiagnosticSample(0, "laser", 10.0), now_mono=10.6, timeout_s=0.5)
    assert (v.mode, v.reason) == ("PROTECTIVE_STOP", "DIAGNOSTIC_STALE")


def test_timeout_boundary_is_inclusive():
    v = assess_diagnostic(DiagnosticSample(0, "laser", 10.0), now_mono=10.5, timeout_s=0.5)
    assert v.mode == "NORMAL_CANDIDATE"


def test_software_stop_wins_over_ok():
    v = assess_diagnostic(DiagnosticSample(0, "laser", 10.0), now_mono=10.2, timeout_s=0.5,
                          sw_stop_latched=True)
    assert (v.mode, v.reason) == ("SW_STOP_LATCHED", "SW_STOP_REQUESTED")


def test_recovery_is_not_automatic():
    v = assess_diagnostic(DiagnosticSample(0, "laser", 10.0), now_mono=10.2, timeout_s=0.5,
                          prior_protective_stop=True)
    assert (v.mode, v.reason, v.requires_manual_recovery) == ("RECOVERY_REQUIRED", "MANUAL_RECOVERY_REQUIRED", True)


def test_recovery_not_allowed_while_error_persists():
    v = assess_diagnostic(DiagnosticSample(2, "laser", 10.0), now_mono=10.2, timeout_s=0.5,
                          prior_protective_stop=True)
    assert v.mode == "PROTECTIVE_STOP"


def test_invalid_future_time_fail_closed():
    v = assess_diagnostic(DiagnosticSample(0, "laser", 11.0), now_mono=10.0, timeout_s=0.5)
    assert (v.mode, v.reason) == ("PROTECTIVE_STOP", "INVALID_INPUT")


def test_invalid_unknown_level_fail_closed():
    v = assess_diagnostic(DiagnosticSample(9, "laser", 10.0), now_mono=10.1, timeout_s=0.5)
    assert (v.mode, v.reason) == ("PROTECTIVE_STOP", "INVALID_INPUT")