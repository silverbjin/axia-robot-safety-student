"""P1-T06 scan-only fault plan; no clock or motor command publication."""
from dataclasses import dataclass
from enum import Enum


SCAN_IN = "/scan"
SCAN_OUT = "/safety/scan"
FUTURE_OFFSET_NS = 2_000_000_000


class FaultMode(str, Enum):
    NORMAL = "NORMAL"
    DROP_SCAN = "DROP_SCAN"
    STALE_STAMP = "STALE_STAMP"
    FUTURE_STAMP = "FUTURE_STAMP"


@dataclass
class ScanFaultPlan:
    mode: FaultMode = FaultMode.NORMAL
    last_normal_stamp_ns: int | None = None

    def select(self, mode):
        if not isinstance(mode, FaultMode):
            raise ValueError("invalid fault mode")
        if mode == FaultMode.STALE_STAMP and self.last_normal_stamp_ns is None:
            raise ValueError("no prior valid stamp for stale replay")
        self.mode = mode

    def output_stamp_ns(self, incoming_stamp_ns: int, *, now_ros_ns: int) -> int | None:
        if type(incoming_stamp_ns) is not int or incoming_stamp_ns <= 0:
            raise ValueError("invalid scan stamp")
        if type(now_ros_ns) is not int or now_ros_ns < 0:
            raise ValueError("invalid ROS clock")
        if self.mode == FaultMode.DROP_SCAN:
            return None
        if self.mode == FaultMode.STALE_STAMP:
            if self.last_normal_stamp_ns is None:
                raise ValueError("no valid initial scan")
            return self.last_normal_stamp_ns
        if self.mode == FaultMode.FUTURE_STAMP:
            return max(incoming_stamp_ns, now_ros_ns) + FUTURE_OFFSET_NS
        self.last_normal_stamp_ns = incoming_stamp_ns
        return incoming_stamp_ns
