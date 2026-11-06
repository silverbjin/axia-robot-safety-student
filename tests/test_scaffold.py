"""Always-run template smoke; never means student TODO implementation is complete."""
from axia_student.stop_latch import SoftwareStopLatch


def test_todo_api_exists():
    latch = SoftwareStopLatch()
    assert latch.state == 'BOOT_SAFE'
    for name in ('request_stop', 'fault_cleared', 'rearm', 'motion_allowed'):
        assert callable(getattr(latch, name))
