"""Run explicitly for TDD RED. These tests MUST fail until TODO is implemented."""
from axia_student.stop_latch import SoftwareStopLatch


def test_boot_safe_blocks_movement():
    subject = SoftwareStopLatch()
    assert subject.motion_allowed() is False


def test_stop_remains_latched_after_fault_cleared():
    subject = SoftwareStopLatch()
    subject.request_stop('synthetic_scan_missing')
    subject.fault_cleared()
    assert subject.motion_allowed() is False


def test_unapproved_rearm_does_not_allow_movement():
    subject = SoftwareStopLatch()
    subject.request_stop('synthetic_scan_missing')
    subject.fault_cleared()
    assert subject.rearm(operator_approved=False) is False
    assert subject.motion_allowed() is False

def test_rearm_requires_cleared_fault():
    subject = SoftwareStopLatch()
    subject.request_stop('synthetic_scan_missing')
    assert subject.rearm(operator_approved=True) is False
    assert subject.motion_allowed() is False


def test_explicit_rearm_after_clear_can_accept_new_goal():
    subject = SoftwareStopLatch()
    subject.request_stop('synthetic_scan_missing')
    subject.fault_cleared()
    assert subject.motion_allowed() is False  # clearing is not rearm
    assert subject.rearm(operator_approved=True) is True
    assert subject.motion_allowed() is True  # permission only; no goal is sent
