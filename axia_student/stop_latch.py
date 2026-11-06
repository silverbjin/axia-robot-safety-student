"""Student TODO: abstract SW Stop latch only, no hardware authority.

This code MUST NOT be wired directly to any real robot drive or certified E-Stop.
"""


class SoftwareStopLatch:
    def __init__(self):
        # TODO: establish BOOT_SAFE and motion denied by default.
        self.state = 'BOOT_SAFE'

    def request_stop(self, reason: str) -> None:
        """TODO: create a latched protective stop."""
        raise NotImplementedError('student TODO: request_stop')

    def fault_cleared(self) -> None:
        """TODO: acknowledge fault cleared without automatically rearming."""
        raise NotImplementedError('student TODO: fault_cleared')

    def rearm(self, operator_approved: bool) -> bool:
        """TODO: explicitly rearm only when safe and operator-approved."""
        raise NotImplementedError('student TODO: rearm')

    def motion_allowed(self) -> bool:
        """TODO: fail closed in BOOT_SAFE / any latched Stop state."""
        raise NotImplementedError('student TODO: motion_allowed')
