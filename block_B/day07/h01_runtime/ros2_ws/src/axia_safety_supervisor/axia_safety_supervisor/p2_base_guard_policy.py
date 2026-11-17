"""Educational P2 base command TTL guard; not a certified E-Stop.

Only safeguards a running guard against a crashed upstream Supervisor / CM.
No guarantee if guard, ROS bridge, Gazebo, or host itself fails. Do not claim
industrial functional safety or hardware E-Stop equivalence.
"""
from collections import deque
from dataclasses import dataclass, field
import math

TTL_SEC = 0.5  # Original proposed command timeout, never CI-relaxed.
# G06 Owner raw: CM last healthy output ~25ms before SIGKILL, action SUCCEEDED
# 346ms after fault, well before the former 0.5s missing-CM latch.
# Actual healthy CM samples were spaced <=91ms; fail closed after 150ms
# without a new CM output (three nominal 20Hz periods). This tightens the
# CM upstream watchdog; the original 0.5s Supervisor timeout is unchanged.
CM_TTL_SEC = 0.15
# Bounded time to distinguish a delayed, exact historical CM response from
# a genuine command violation. This does NOT relax either upstream TTL.
# Unknown attribution sends ZERO and never forwards an old faster command.
ASYNC_RECONCILIATION_GRACE_SEC = 0.12
MAX_LINEAR_MPS = 0.46  # Official Waffle simulator velocity bounds, not safety certification.
MAX_ANGULAR_RPS = 1.9


@dataclass(frozen=True)
class Motion:
    linear_x: float = 0.0
    angular_z: float = 0.0
    linear_y: float = 0.0
    linear_z: float = 0.0
    angular_x: float = 0.0
    angular_y: float = 0.0


ZERO = Motion()


def valid(command):
    return isinstance(command, Motion) and all(
        isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)
        for v in (command.linear_x, command.angular_z, command.linear_y,
                  command.linear_z, command.angular_x, command.angular_y)
    ) and not any((command.linear_y, command.linear_z,
                   command.angular_x, command.angular_y)) and (
        abs(command.linear_x) <= MAX_LINEAR_MPS and abs(command.angular_z) <= MAX_ANGULAR_RPS
    )


@dataclass
class State:
    supervisor: Motion | None = None
    collision_monitor: Motion | None = None
    supervisor_rx: float | None = None
    monitor_rx: float | None = None
    last_tick: float | None = None
    last_emitted: Motion = ZERO
    ever_moved: bool = False
    # A CM output is an asynchronous delayed copy/slowdown of a prior Supervisor
    # command. Match only recent actual source commands (never a free pass).
    supervisor_history: deque = field(default_factory=lambda: deque(maxlen=64))
    latched: bool = False
    reason: str = "BOOT_ZERO"
    # First host-monotonic tick when a plausible delayed CM command is seen.
    # A recovered pair clears this; a persistent mismatch LATCHES.
    pending_cm_reconciliation_since: float | None = None
    # Independent trusted Supervisor FSM status observed on its existing ROS
    # topic, used ONLY to distinguish NORMAL Goal controller pauses from an
    # actual protective or manual software stop. Twist has no stop identity.
    supervisor_state: str | None = None
    supervisor_state_rx: float | None = None
    supervisor_goal_id: str | None = None
    supervisor_healthy: bool = False
    supervisor_stop_reason: str = ""

    def receive_supervisor_state(
        self, state: str | None, now: float, *,
        goal_id: str | None = None, healthy: bool = False,
        stop_reason: str = "",
    ):
        if not isinstance(now, (int, float)) or not math.isfinite(now) or (
            self.supervisor_state_rx is not None and now < self.supervisor_state_rx
        ):
            self.latched, self.reason = True, "CLOCK_REGRESSION"
            return
        self.supervisor_state_rx = now
        self.supervisor_state = state if state in (
            "BOOT_SAFE", "NORMAL", "LIMITED", "PROTECTIVE_STOP",
            "SW_STOP_LATCHED", "RECOVERY_REQUIRED",
        ) else None
        self.supervisor_goal_id = goal_id if (
            isinstance(goal_id, str) and len(goal_id) == 32
            and all(c in "0123456789abcdefABCDEF" for c in goal_id)
        ) else None
        self.supervisor_healthy = healthy is True
        self.supervisor_stop_reason = stop_reason if isinstance(stop_reason, str) else "INVALID"

    def receive(self, source: str, command: Motion, now: float):
        if source not in ("supervisor", "collision_monitor"):
            self.latched, self.reason = True, "UNKNOWN_SOURCE"
            return
        if not isinstance(now, (int, float)) or not math.isfinite(now) or (
            self.last_tick is not None and now < self.last_tick
        ):
            self.latched, self.reason = True, "CLOCK_REGRESSION"
            return
        previous = self.supervisor_rx if source == 'supervisor' else self.monitor_rx
        if previous is not None and now < previous:
            self.latched, self.reason = True, 'CLOCK_REGRESSION'
            return
        if not valid(command):
            self.latched, self.reason = True, "BAD_COMMAND"
            return
        if source == "supervisor":
            self.supervisor, self.supervisor_rx = command, now
            self.supervisor_history.append((now, command))
        else:
            # PIYOmtc8 REAL WSL2: a CM callback matching the then-current
            # healthy Supervisor command arrived at 125.976s. A *later*
            # Supervisor Twist (125.046s relative to session start) made
            # the pair look mismatched at the next Guard tick, while the
            # old pending window (from 125.908s) was still running.
            # Guard must recognize an actually reconciled pair AT RECEIPT,
            # not only when its 20Hz timer finally executes. Otherwise a
            # later valid controller update inherits an unrelated expired
            # pending window and falsely latches the supervised Goal.
            #
            # Clear ONLY the pending ZERO-only timer, never the safety latch,
            # never forward command from receive(), never extend TTL/grace.
            # A repeated unchanged CM packet, 30%-slow/unmatched packet,
            # unauthorised Goal, STOP, stale FSM or expired initial pending
            # cannot rearm the grace period.
            previous_cm = self.collision_monitor
            if (
                self.pending_cm_reconciliation_since is not None
                and 0 <= now - self.pending_cm_reconciliation_since
                <= ASYNC_RECONCILIATION_GRACE_SEC
                and self.ever_moved and self.last_emitted == ZERO
                and not self.latched
                and previous_cm != command and command != ZERO
                and self.supervisor is not None
                and command == self.supervisor
                and self.supervisor_rx is not None
                and 0 <= now - self.supervisor_rx <= CM_TTL_SEC
                and self.supervisor_state in ("NORMAL", "LIMITED")
                and self.supervisor_healthy
                and self.supervisor_goal_id is not None
                and self.supervisor_stop_reason == ""
                and self.supervisor_state_rx is not None
                and 0 <= now - self.supervisor_state_rx
                <= ASYNC_RECONCILIATION_GRACE_SEC
            ):
                self.pending_cm_reconciliation_since = None
            self.collision_monitor, self.monitor_rx = command, now

    def diagnostic_snapshot(self, now: float) -> dict:
        """Sample actual Guard callback state at the SAME monotonic tick.

        Twist has no origin sequence: this proves only what Guard compared,
        not which upstream Supervisor message the CM actually processed.
        No robot motion changes or extra safety timers.
        """
        def motion_value(value):
            return None if value is None else {
                "linear_x": value.linear_x, "angular_z": value.angular_z,
            }
        return {
            "tick_monotonic": now,
            "supervisor_rx_monotonic": self.supervisor_rx,
            "cm_rx_monotonic": self.monitor_rx,
            "supervisor_age_sec": None if self.supervisor_rx is None else now - self.supervisor_rx,
            "supervisor_fsm": self.supervisor_state,
            "supervisor_fsm_age_sec": None if self.supervisor_state_rx is None else now - self.supervisor_state_rx,
            "supervisor_authorized_goal": self.supervisor_goal_id is not None,
            "cm_age_sec": None if self.monitor_rx is None else now - self.monitor_rx,
            "supervisor": motion_value(self.supervisor),
            "collision_monitor": motion_value(self.collision_monitor),
            "reconciliation_since_monotonic": self.pending_cm_reconciliation_since,
            "last_emitted": motion_value(self.last_emitted),
            "latched": self.latched,
            "reason": self.reason,
        }

    def step(self, now: float) -> Motion:
        if not isinstance(now, (int, float)) or not math.isfinite(now) or (
            self.last_tick is not None and now < self.last_tick
        ):
            self.latched, self.reason = True, "CLOCK_REGRESSION"
        self.last_tick = now if isinstance(now, (int, float)) and math.isfinite(now) else self.last_tick
        if self.latched:
            self.last_emitted = ZERO
            return ZERO
        fresh = (self.supervisor_rx is not None and 0 <= now - self.supervisor_rx <= TTL_SEC
                 and self.monitor_rx is not None and 0 <= now - self.monitor_rx <= CM_TTL_SEC)
        if not fresh:
            # Do not poison boot / idle while CM is not publishing commands.
            # Once this node *actually forwarded motion*, any missing input
            # latches until an explicitly fresh full-session startup.
            if self.ever_moved:
                self.latched, self.reason = True, "UPSTREAM_STALE_AFTER_MOTION"
            else:
                self.reason = "NO_FRESH_PAIR"
            self.last_emitted = ZERO
            return ZERO
        sup, cm = self.supervisor, self.collision_monitor
        if not valid(sup) or not valid(cm):
            self.latched, self.reason = True, "BAD_COMMAND"
            self.last_emitted = ZERO
            return ZERO
        # The trusted FSM may reach a STOP before the independent Twist topic.
        # A protective/software stop is never a controller transient; latch
        # even if CM already emitted ZERO. This does not alter the ZERO output.
        if self.supervisor_state in ("PROTECTIVE_STOP", "SW_STOP_LATCHED"):
            self.latched = True
            self.reason = ("CM_EXCEEDS_SUPERVISOR"
                           if sup == ZERO and cm != ZERO else "SUPERVISOR_SAFETY_STOP")
            self.last_emitted = ZERO
            return ZERO
        # Nav2 CM receives Supervisor twists asynchronously. Comparing the
        # latest CM output to only the *latest* Supervisor twist falsely trips
        # on valid turns (old angular > 0, next angular < 0). Match to an
        # actually received Supervisor twist within the unchanged TTL instead.
        # All candidate commands retain original per-axis limits and direction
        # checks; unknown/excess CM outputs remain fail-closed.
        while self.supervisor_history and now - self.supervisor_history[0][0] > TTL_SEC:
            self.supervisor_history.popleft()
        def permitted(origin):
            return (abs(cm.linear_x) <= abs(origin.linear_x) + 0.01
                    and abs(cm.angular_z) <= abs(origin.angular_z) + 0.02
                    and cm.linear_x * origin.linear_x >= 0
                    and cm.angular_z * origin.angular_z >= 0)
        # The latest Supervisor command still has absolute stop priority.
        # History may explain a tiny asynchronous angular sign flip, but may
        # NEVER allow a delayed CM command to override a fresh SW Stop,
        # a linear slowdown, or a substantial direction reversal.
        current_stop_or_excess = (
            (sup == ZERO and cm != ZERO)
            or abs(cm.linear_x) > abs(sup.linear_x) + 0.01
            or abs(cm.angular_z) > abs(sup.angular_z) + 0.02
            or cm.linear_x * sup.linear_x < 0
            or (cm.angular_z * sup.angular_z < 0
                and min(abs(cm.angular_z), abs(sup.angular_z)) > 0.02)
        )
        history_matches = any(permitted(origin) for _, origin in self.supervisor_history)
        # Actual public CI moving-Goal RED: while FSM stayed healthy NORMAL /
        # GOAL_AUTHORIZED, Nav2 intermittently commanded ZERO. The genuine CM
        # had not yet returned the previous 30%-slowed Twist (38-43ms old).
        # In this *narrow* case, ZERO is always the final robot command, but
        # a permanent latch would needlessly cancel the authorized Goal.
        # Require a recent, healthy NORMAL/LIMITED FSM with a real owned Goal,
        # and an exact 30% two-axis CM match from the recent Supervisor input.
        # Unknown provenance/state, excess/reverse, actual STOP and TTLs
        # preserve immediate fail-closed latch. Never forward the old CM Twist.
        # Real Harmonic/Nav2 CI #42973158645: normal turn transitioned
        # from (+0.037287,+0.021350) to (-0.003210,+0.090366) while CM
        # still carried the exact prior 30%-slow (+0.011186,+0.006405).
        # Its 36ms delay is within existing CM TTL, but the new tiny
        # (<.005m/s) reverse triggered a spurious permanent Goal cancel.
        # Treat ONLY a matched historical 30%-slow packet as an ambiguous
        # controller transition. The *only* output is ZERO for at most
        # 120ms; protect STOP, material reverse, stale/missing and unowned.
        nearzero_normal_turn = (
            sup != ZERO and cm != ZERO
            and sup.linear_x * cm.linear_x < 0
            and 0 < abs(sup.linear_x) <= .005
            and .01 < abs(cm.linear_x) <= .015
            and sup.angular_z * cm.angular_z >= 0
        )
        authorized_controller_zero = (
            self.ever_moved and cm != ZERO
            and (sup == ZERO or nearzero_normal_turn)
            and self.supervisor_state in ("NORMAL", "LIMITED")
            and self.supervisor_healthy
            and self.supervisor_stop_reason == ""
            and self.supervisor_goal_id is not None
            and self.supervisor_state_rx is not None
            and 0 <= now - self.supervisor_state_rx <= ASYNC_RECONCILIATION_GRACE_SEC
            and any(
                at < self.supervisor_rx
                and 0 <= now - at <= CM_TTL_SEC
                and origin != ZERO
                and abs(cm.linear_x - 0.30 * origin.linear_x) < 1e-6
                and abs(cm.angular_z - 0.30 * origin.angular_z) < 1e-6
                for at, origin in self.supervisor_history
            )
        )
        if authorized_controller_zero:
            if self.pending_cm_reconciliation_since is None:
                self.pending_cm_reconciliation_since = now
            if 0 <= now - self.pending_cm_reconciliation_since <= ASYNC_RECONCILIATION_GRACE_SEC:
                self.reason = "AWAITING_CM_RECONCILIATION_ZERO"
                self.last_emitted = ZERO
                return ZERO
        if current_stop_or_excess or not history_matches:
            # The ROS 2 /cmd_vel_supervised -> Collision Monitor ->
            # /cmd_vel_pre_guard pipeline is asynchronous. An actual Owner G07
            # trace showed a delayed CM output matching the prior Supervisor
            # sample while the newest Supervisor had already reduced speed.
            #
            # This is NOT proof of CM origin (Twist carries no sequence).
            # Consequently NEVER forward the disputed older speed. Allow only
            # a SHORT all-ZERO reconciliation window while fresh messages can
            # catch up; anything unresolved latches. STOP, material reverse,
            # unmatched excess and missing inputs retain immediate latch.
            linear_over = abs(cm.linear_x) > abs(sup.linear_x) + 0.01
            angular_over = abs(cm.angular_z) > abs(sup.angular_z) + 0.02
            reversed_linear = cm.linear_x * sup.linear_x < 0
            reversed_angular = (cm.angular_z * sup.angular_z < 0
                                and min(abs(cm.angular_z), abs(sup.angular_z)) > 0.02)
            partial_stop_overridden = (
                (abs(sup.linear_x) <= 0.01 and abs(cm.linear_x) > 0.01)
                or (abs(sup.angular_z) <= 0.02 and abs(cm.angular_z) > 0.02)
            )
            older_matching_origin = any(
                at < self.supervisor_rx and permitted(origin)
                and 0 <= now - at <= TTL_SEC
                for at, origin in self.supervisor_history
            )
            # Owner Kn2kH5fL: Supervisor crossed +0.001181 m/s while the
            # delayed CM still held -0.000861 m/s. Both are below the
            # existing 0.01 m/s per-axis comparison tolerance. Their
            # opposite signs are NOT sufficient proof of a material reverse.
            # Treat as ambiguous only when an exact recent historical
            # Supervisor command explains the CM output. Emit full ZERO
            # during reconciliation; NEVER forward the disputed CM twist.
            # This does NOT exempt explicit ZERO, >0.01m/s reverse,
            # unknown source, directional angular reversal or stale input.
            near_zero_linear_crossing = (
                reversed_linear
                and abs(sup.linear_x) <= 0.01
                and abs(cm.linear_x) <= 0.01
            )
            # Actual Owner KcA1lXOe: the CM has a delayed (0.30x) response
            # to a nearly-stopped old Supervisor (+0.000717m/s) while the
            # Supervisor has already commanded a legitimate new negative
            # direction (-0.018398m/s). Previously, the historical command
            # matched, but "not reversed_linear" rejected it before the
            # old CM output (-untrusted for current motion-) could catch up.
            #
            # This exception is for ZERO-ONLY reconciliation, *never* CM
            # forwarding. Require matching BOTH vector components to the
            # frozen G07 slowdown_ratio=0.30 using 1e-6 float resolution.
            # The candidate origin must predate the latest Supervisor.
            # Require the old *CM output* (not the pre-slowdown origin) to be
            # within the EXISTING 0.01m/s ambiguity bound. An old Supervisor
            # at -0.01649 produces a safe-to-HOLD -0.00495 CM at 30%:
            # a prior additional <=0.01 origin cap falsely latched G07.
            # This only authorizes full ZERO hold, never older CM motion.
            # Actual actionable CM reverse or non-30%-matched output latches.
            # Real Owner tYWDqbSM: the authentic old 30%-slowed CM value
            # (+0.010134m/s) was 0.000134 above the 0.01 ambiguity cut
            # while the latest healthy NORMAL Goal requested -0.018917m/s.
            # Admit this *only* as bounded ZERO-only reconciliation:
            # current reverse <=0.02, CM <=0.015, verified NORMAL Goal
            # and a fresh FSM with empty stop_reason. The historical
            # two-axis exact 30% origin match below remains mandatory.
            # No disputed old velocity is ever forwarded; >=120ms unresolved,
            # material reverse, stale CM and explicit SW/PROTECTIVE STOP latch.
            field_healthy_small_reverse = (
                abs(cm.linear_x) <= 0.015
                and abs(sup.linear_x) <= 0.02
                and self.supervisor_state in ("NORMAL", "LIMITED")
                and self.supervisor_healthy
                and self.supervisor_goal_id is not None
                and self.supervisor_stop_reason == ""
                and self.supervisor_state_rx is not None
                and 0 <= now - self.supervisor_state_rx <= ASYNC_RECONCILIATION_GRACE_SEC
            )
            historical_slowdown_direction_crossing = (
                reversed_linear
                and (abs(cm.linear_x) <= 0.01 or field_healthy_small_reverse)
                and any(
                    at < self.supervisor_rx
                    and 0 <= now - at <= TTL_SEC
                    and origin.linear_x != 0
                    and origin.linear_x * sup.linear_x < 0
                    and origin.linear_x * cm.linear_x > 0
                    and abs(cm.linear_x - 0.30 * origin.linear_x) < 1e-6
                    and abs(cm.angular_z - 0.30 * origin.angular_z) < 1e-6
                    for at, origin in self.supervisor_history
                )
            )
            plausible_async_skew = (
                self.ever_moved and sup != ZERO and cm != ZERO
                and history_matches and older_matching_origin
                and (linear_over or angular_over or near_zero_linear_crossing
                     or historical_slowdown_direction_crossing)
                and (not reversed_linear or near_zero_linear_crossing
                     or historical_slowdown_direction_crossing)
                and not reversed_angular
                and not partial_stop_overridden
            )
            if plausible_async_skew:
                if self.pending_cm_reconciliation_since is None:
                    self.pending_cm_reconciliation_since = now
                if (0 <= now - self.pending_cm_reconciliation_since
                        <= ASYNC_RECONCILIATION_GRACE_SEC):
                    self.reason = "AWAITING_CM_RECONCILIATION_ZERO"
                    self.last_emitted = ZERO
                    return ZERO
            self.latched, self.reason = True, "CM_EXCEEDS_SUPERVISOR"
            self.last_emitted = ZERO
            return ZERO
        # Only a fresh, currently permitted CM output resumes forward motion.
        # An absent/expired input still latches via the unchanged TTL above.
        self.pending_cm_reconciliation_since = None
        self.reason = "FORWARDING_MONITORED_CM"
        self.last_emitted = cm
        if cm != ZERO:
            self.ever_moved = True
        return cm
