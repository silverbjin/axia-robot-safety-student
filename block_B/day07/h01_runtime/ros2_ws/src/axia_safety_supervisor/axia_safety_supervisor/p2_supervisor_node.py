"""P2-only Supervisor variant: exact guard graph, P1 default untouched."""

import json
import time

import rclpy
from rclpy.executors import ExternalShutdownException
from .p2_shutdown_context import is_context_waitset_shutdown, is_context_publish_shutdown
from std_msgs.msg import String

from .fsm import SafetyState, transition
from .p3_g09_risk_policy import RiskState, apply_verdict, expired_verdict
from .supervisor_node import SafetySupervisorNode

TWIST = 'geometry_msgs/msg/Twist'


class P2SupervisorNode(SafetySupervisorNode):
    def __init__(self):
        super().__init__()
        # Default disabled. Only the isolated public S04 demo enables this
        # educational fixture-to-FSM LIMIT adapter. This is not a trusted
        # person detector and never publishes motor /cmd_vel or Nav2 Goals.
        self.declare_parameter("p3_fixture_risk_bridge_enabled",False)
        self._s04_enabled=(
            self.get_parameter("p3_fixture_risk_bridge_enabled").value is True)
        self._s04_risk=RiskState()
        self._s04_unique_source=False
        self._s04_graph_checked=False
        if self._s04_enabled:
            self._s04_audit_pub=self.create_publisher(
                String,"/axia/p3/g09/risk_applied",10)
            self.create_subscription(
                String,"/axia/p3/g09/verdict",self._s04_receive_verdict,10)
            self.get_logger().warning(
                "S04 synthetic fixture verdict may ONLY reduce normal "
                "Goal speed via existing Supervisor FSM; no E-Stop claim")

    def _s04_audit(self, *, seq, verdict, action):
        msg=String()
        msg.data=json.dumps({
            "seq":seq,"verdict":verdict,"action":action,
            "state":self._state.state.value,
            "goal_uuid":self._state.authorized_goal_id,
            "host_monotonic_sec":time.monotonic(),
            "sim_fixture_only":True,"certified_estop":False,
            "formal_g09_accepted":False,
        },sort_keys=True)
        self._s04_audit_pub.publish(msg)

    def _s04_receive_verdict(self,msg):
        if not self._s04_enabled:
            return
        now=time.monotonic()
        if not self._s04_graph_checked:
            pubs=self.get_publishers_info_by_topic("/axia/p3/g09/verdict")
            self._s04_unique_source=(
                len(pubs)==1 and pubs[0].node_name=="axia_p3_g09_fixture_oracle"
                and pubs[0].topic_type=="std_msgs/msg/String")
            self._s04_graph_checked=True
        try:payload=json.loads(msg.data)
        except (TypeError,ValueError,UnicodeError):payload=None
        goal=self._state.authorized_goal_id
        next_state,action=apply_verdict(
            self._s04_risk,payload,now_mono=now,
            unique_source=self._s04_unique_source,
            owned_goal=isinstance(goal,str) and bool(goal),
            healthy=self._state.healthy)
        self._s04_risk=next_state
        if (next_state.limited_by_risk and self._state.state in
                (SafetyState.NORMAL,SafetyState.LIMITED)
                and self._state.healthy and goal):
            self._state=transition(self._state,"limit_on")
        self._s04_audit(
            seq=(payload.get("seq") if isinstance(payload,dict) else None),
            verdict=next_state.last_verdict,action=action)

    def _tick(self):
        # Original P1 timers, nav2 cancel, scan/CM/Guard watchdog and command
        # output remain authoritative. Never override a protective SW STOP.
        super()._tick()
        if not getattr(self,"_s04_enabled",False):
            return
        now=time.monotonic()
        if (self._state.state==SafetyState.NORMAL
                and self._state.healthy
                and self._state.authorized_goal_id
                and not self._s04_risk.limited_by_risk
                and expired_verdict(self._s04_risk,now_mono=now)):
            from dataclasses import replace
            self._s04_risk=replace(
                self._s04_risk,limited_by_risk=True,last_verdict="U")
            self._state=transition(self._state,"limit_on")
            self._s04_audit(
                seq=self._s04_risk.last_seq,verdict="U",
                action="LIMIT_ON_VERDICT_STALE")

    def _graph_ready(self):
        # This check is diagnostic graph topology, NOT ROS access control.
        final = self.get_publishers_info_by_topic('/cmd_vel')
        monitored = self.get_publishers_info_by_topic('/cmd_vel_pre_guard')
        final_sub = self.get_subscriptions_info_by_topic('/cmd_vel')
        monitored_sub = self.get_subscriptions_info_by_topic('/cmd_vel_pre_guard')
        sup_sub = self.get_subscriptions_info_by_topic('/cmd_vel_supervised')
        return (
            len(final) == 1 and final[0].node_name == 'axia_base_command_guard'
            and final[0].topic_type == TWIST
            and len(monitored) == 1 and monitored[0].node_name == 'collision_monitor'
            and monitored[0].topic_type == TWIST
            and any(x.node_name == 'axia_base_command_guard' and x.topic_type == TWIST
                    for x in monitored_sub)
            and any(x.node_name == 'collision_monitor' and x.topic_type == TWIST
                    for x in sup_sub)
            and any(x.topic_type == TWIST for x in final_sub)
        )


def main(args=None):
    rclpy.init(args=args)
    node = None
    try:
        node = P2SupervisorNode()
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    except Exception as exc:
        # WSL2 Owner vJpsc6Wy: rclpy WaitSet may race the ROS SIGINT
        # context invalidation. Never hide a still-active ROS exception.
        # Exact post-SIGINT context invalidations only. A live Publisher
        # fault still raises and blocks acceptance, even if wording matches.
        context_ok=rclpy.ok()
        if not (is_context_waitset_shutdown(exc,context_ok=context_ok)
                or is_context_publish_shutdown(exc,context_ok=context_ok)):
            raise
    finally:
        if node is not None:
            node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
