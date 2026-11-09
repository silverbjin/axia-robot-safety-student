"""ROS-free data/timeout checks. Actual steady timer and ROS callbacks pending.

+Inf is a common no-return LaserScan reading, NOT an observed free ray.
This minimal G04 unit policy requires at least one finite beam; a production
front-sector coverage policy and real sensor samples remain unapproved.
"""
from dataclasses import dataclass
import math
from typing import Optional, Sequence


@dataclass(frozen=True)
class ScanPolicy:
    frame_id: str
    timeout_sec: float
    future_tolerance_ns: int
    sector_min_rad: Optional[float] = None
    sector_max_rad: Optional[float] = None
    min_finite_fraction: float = 0.6
    max_missing_run: int = 1


@dataclass(frozen=True)
class ScanPacket:
    stamp_ns: int
    frame_id: str
    ranges: Sequence[float]
    range_min: float
    range_max: float
    angle_min: float
    angle_max: float
    angle_increment: float


@dataclass(frozen=True)
class CheckResult:
    ok: bool
    reason: str


def _finite(x):
    return type(x) in (float, int) and math.isfinite(x)


def _failure(reason):
    return CheckResult(False, reason)


def check_scan(scan: ScanPacket, *, now_ros_ns: int, prior_stamp_ns: Optional[int],
               policy: ScanPolicy) -> CheckResult:
    """Conservative synthetic validation, not final collision-zone coverage."""
    if not isinstance(scan.frame_id, str) or scan.frame_id != policy.frame_id or not scan.frame_id:
        return _failure("FRAME_MISMATCH")
    if (type(scan.stamp_ns) is not int or scan.stamp_ns <= 0 or
            type(now_ros_ns) is not int or now_ros_ns < 0):
        return _failure("CLOCK_INVALID")
    if prior_stamp_ns is not None and scan.stamp_ns <= prior_stamp_ns:
        return _failure("STALE_STAMP")
    if (type(policy.future_tolerance_ns) is not int or policy.future_tolerance_ns < 0 or
            scan.stamp_ns > now_ros_ns + policy.future_tolerance_ns):
        return _failure("FUTURE_STAMP")
    if (not all(_finite(x) for x in (scan.range_min, scan.range_max,
                                  scan.angle_min, scan.angle_max, scan.angle_increment)) or
            scan.range_min < 0 or scan.range_max <= scan.range_min or
            scan.angle_increment <= 0 or scan.angle_max < scan.angle_min):
        return _failure("INVALID_METADATA")
    count = int(round((scan.angle_max - scan.angle_min) / scan.angle_increment)) + 1
    if not (1 <= count <= 200000) or len(scan.ranges) != count:
        return _failure("INVALID_LENGTH")
    finite_beams = 0
    for distance in scan.ranges:
        if type(distance) not in (float, int):
            return _failure("INVALID_RANGE")
        if math.isinf(distance) and distance > 0:
            continue  # No return; does not count as observed finite coverage.
        if not math.isfinite(distance):
            return _failure("INVALID_RANGE")
        if distance < scan.range_min or distance > scan.range_max:
            return _failure("INVALID_RANGE")
        finite_beams += 1
    if policy.sector_min_rad is None or policy.sector_max_rad is None:
        return _failure("COVERAGE_UNCONFIGURED")
    if (not _finite(policy.sector_min_rad) or not _finite(policy.sector_max_rad)
            or policy.sector_min_rad >= policy.sector_max_rad
            or policy.sector_max_rad - policy.sector_min_rad > 2 * math.pi
            or not _finite(policy.min_finite_fraction)
            or not 0 < policy.min_finite_fraction <= 1
            or type(policy.max_missing_run) is not int or policy.max_missing_run < 0):
        return _failure("COVERAGE_CONFIG_INVALID")

    # Official TurtleBot3 Waffle Gazebo sends /scan with 360 beams in
    # [0, 2pi], whereas the configured forward sector [-0.35, +0.35]
    # straddles its 0/2pi angular seam. Preserve the FULL configured sector,
    # including rays at both ends, rather than treating the negative-angle
    # half as outside coverage or silently reducing the supervised region.
    span = scan.angle_max - scan.angle_min
    if span > 2 * math.pi + scan.angle_increment:
        return _failure("INVALID_METADATA")
    wraps = (abs(span - 2 * math.pi) <= scan.angle_increment
             and -math.pi <= policy.sector_min_rad
             and policy.sector_max_rad <= math.pi)
    if not wraps and (policy.sector_min_rad < scan.angle_min - 1e-6
                      or policy.sector_max_rad > scan.angle_max + 1e-6):
        return _failure("COVERAGE_CONFIG_INVALID")
    selected = []
    for index, distance in enumerate(scan.ranges):
        angle = scan.angle_min + index * scan.angle_increment
        if wraps:
            angle = math.atan2(math.sin(angle), math.cos(angle))
        if policy.sector_min_rad - 1e-6 <= angle <= policy.sector_max_rad + 1e-6:
            selected.append((angle, distance))
    selected.sort(key=lambda pair: pair[0])
    if not selected:
        return _failure("COVERAGE_CONFIG_INVALID")
    # A partial scan covering only positive angles is NOT a valid replacement
    # for a front sector with required negative angles. Every angular gap
    # must have a real beam within one native scan increment.
    tolerance = scan.angle_increment * 1.05 + 1e-6
    if (selected[0][0] - policy.sector_min_rad > tolerance
            or policy.sector_max_rad - selected[-1][0] > tolerance
            or any(right[0] - left[0] > 1.5 * scan.angle_increment + 1e-6
                   for left, right in zip(selected, selected[1:]))):
        return _failure("COVERAGE_CONFIG_INVALID")
    sector = [distance for _angle, distance in selected]
    observed = sum(1 for distance in sector if math.isfinite(distance))
    largest_gap = 0
    current_gap = 0
    for distance in sector:
        if math.isinf(distance):  # Known no-return is not measured clearance.
            current_gap += 1
            largest_gap = max(largest_gap, current_gap)
        else:
            current_gap = 0
    if observed / len(sector) < policy.min_finite_fraction or largest_gap > policy.max_missing_run:
        return _failure("INSUFFICIENT_COVERAGE")
    return CheckResult(True, "VALID")


def _timed_out(*, now_mono: float, last_mono: Optional[float], timeout_sec: float) -> bool:
    if not _finite(now_mono) or not _finite(timeout_sec) or timeout_sec <= 0:
        return True
    if last_mono is None or not _finite(last_mono):
        return True
    age = now_mono - last_mono
    return age < 0 or age > timeout_sec


@dataclass(frozen=True)
class ScanCallbackTiming:
    """Measure real Supervisor callback spacing; never alter stop policy."""
    intervals: int = 0
    over_timeout: int = 0
    invalid_intervals: int = 0
    max_gap_sec: float = 0.0


def observe_scan_callback_interval(stats: ScanCallbackTiming, *, prior_mono: Optional[float],
                                   now_mono: float, timeout_sec: float) -> ScanCallbackTiming:
    if prior_mono is None:
        return stats
    gap = now_mono - prior_mono
    if (not all(_finite(v) for v in (prior_mono, now_mono, timeout_sec, gap))
            or gap < 0 or timeout_sec <= 0):
        return ScanCallbackTiming(
            intervals=stats.intervals + 1,
            over_timeout=stats.over_timeout,
            invalid_intervals=stats.invalid_intervals + 1,
            max_gap_sec=stats.max_gap_sec,
        )
    return ScanCallbackTiming(
        intervals=stats.intervals + 1,
        over_timeout=stats.over_timeout + int(gap > timeout_sec),
        invalid_intervals=stats.invalid_intervals,
        max_gap_sec=max(stats.max_gap_sec, gap),
    )


def scan_callback_deadline_breached(before: ScanCallbackTiming,
                                   after: ScanCallbackTiming) -> bool:
    """A late newly arrived scan cannot erase the missed timeout deadline."""
    return (after.over_timeout > before.over_timeout
            or after.invalid_intervals > before.invalid_intervals)


def scan_timed_out(*, now_mono: float, last_rx_mono: Optional[float],
                   timeout_sec: float) -> bool:
    return _timed_out(now_mono=now_mono, last_mono=last_rx_mono, timeout_sec=timeout_sec)


def cmd_timed_out(*, now_mono: float, last_cmd_mono: Optional[float],
                  timeout_sec: float, motion_expected: bool) -> bool:
    return _timed_out(now_mono=now_mono, last_mono=last_cmd_mono,
                      timeout_sec=timeout_sec) if motion_expected is True else False


def clock_fault(*, now_mono: float, last_clock_mono: Optional[float],
                current_ros_ns: int, previous_ros_ns: int,
                timeout_sec: float) -> Optional[str]:
    if type(current_ros_ns) is not int or type(previous_ros_ns) is not int or current_ros_ns < 0:
        return "CLOCK_INVALID"
    if current_ros_ns < previous_ros_ns:
        return "CLOCK_REGRESSION"
    if _timed_out(now_mono=now_mono, last_mono=last_clock_mono, timeout_sec=timeout_sec):
        return "CLOCK_STALLED"
    return None
