"""D03 public tests: synthetic, no ROS/Gazebo acceptance."""
from todo_safety import DiagnosticSample, assess_diagnostic

def v(level=0, observed=10.0, now=10.2, **extra):
    return assess_diagnostic(DiagnosticSample(level,"laser",observed),
                             now_mono=now,timeout_s=0.5,**extra)

def test_ok_is_not_motion_authorization():
    a=v()
    assert (a.mode,a.reason,a.requires_manual_recovery)==("NORMAL_CANDIDATE","DIAGNOSTIC_OK",False)

def test_warning_requests_limited_candidate():
    assert (v(1).mode,v(1).reason)==("LIMITED_CANDIDATE","DIAGNOSTIC_WARN")

def test_error_fail_closed():
    a=v(2)
    assert (a.mode,a.reason,a.requires_manual_recovery)==("PROTECTIVE_STOP","DIAGNOSTIC_ERROR",True)

def test_level_stale_fail_closed():
    assert (v(3).mode,v(3).reason)==("PROTECTIVE_STOP","DIAGNOSTIC_LEVEL_STALE")

def test_transport_stale_after_timeout():
    assert (v(now=10.6).mode,v(now=10.6).reason)==("PROTECTIVE_STOP","DIAGNOSTIC_STALE")

def test_timeout_boundary_is_inclusive():
    assert v(now=10.5).mode=="NORMAL_CANDIDATE"

def test_software_stop_wins_over_ok():
    assert (v(sw_stop_latched=True).mode,v(sw_stop_latched=True).reason)==("SW_STOP_LATCHED","SW_STOP_REQUESTED")

def test_recovery_is_not_automatic():
    a=v(prior_protective_stop=True)
    assert (a.mode,a.reason,a.requires_manual_recovery)==("RECOVERY_REQUIRED","MANUAL_RECOVERY_REQUIRED",True)

def test_recovery_not_allowed_while_error_persists():
    assert v(2,prior_protective_stop=True).mode=="PROTECTIVE_STOP"

def test_invalid_future_time_fail_closed():
    assert (v(observed=11.0,now=10.0).mode,v(observed=11.0,now=10.0).reason)==("PROTECTIVE_STOP","INVALID_INPUT")

def test_invalid_unknown_level_fail_closed():
    assert (v(9).mode,v(9).reason)==("PROTECTIVE_STOP","INVALID_INPUT")
