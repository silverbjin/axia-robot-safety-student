"""P2 G05/G06 read-only same-domain pre-crash admission (ROS Jazzy only).

Requires simultaneous actual motion, trusted cmd publisher graph, active
Nav2 goal UUID, advancing /clock, and live Supervisor+independent Guard.
No command publisher, Goal creation, Fault, or safety authorization is returned.
"""
import json
import math
import time

TWIST='geometry_msgs/msg/Twist'


def assess(snapshot, *, now):
    if not isinstance(snapshot,dict) or not isinstance(now,(int,float)) or not math.isfinite(now):
        return False,'NO_LIVE_SNAPSHOT'
    graph=snapshot.get('graph',{})
    for topic,name in (('/cmd_vel','axia_base_command_guard'),
                       ('/cmd_vel_pre_guard','collision_monitor'),
                       ('/cmd_vel_supervised','axia_safety_supervisor')):
        entries=graph.get(topic)
        if not isinstance(entries,list) or len(entries)!=1 or entries[0] != (name,TWIST):
            return False,'PUBLISHER_GRAPH_UNVERIFIED'
    for item in ('odom','final_cmd','pre_guard_cmd','scan','clock','guard','supervisor','action'):
        age=snapshot.get(item+'_at')
        if type(age) not in (float,int) or not math.isfinite(age) or not (0 <= now-age <= 0.5):
            return False,'STALE_OR_MISSING_'+item.upper()
    for key in ('odom_v','cmd_v','pre_guard_v'):
        v=snapshot.get(key)
        if type(v) not in (int,float) or not math.isfinite(v) or abs(v) <= .05:
            return False,'MOVEMENT_NOT_PROVEN_'+key.upper()
    guard=snapshot.get('guard_status',{})
    if guard.get('latched') is not False or guard.get('reason')!='FORWARDING_MONITORED_CM':
        return False,'GUARD_NOT_LIVE_FORWARDING'
    sup=snapshot.get('supervisor_status',{})
    health=sup.get('health_diagnostics',{})
    if (sup.get('state') not in ('NORMAL','LIMITED') or not sup.get('goal_id')
        or sup.get('stop_is_certified_estop') is not False
        or health.get('cm_active') is not True):
        return False,'SUPERVISOR_UNHEALTHY_OR_NO_GOAL'
    if snapshot.get('action_goal_uuid') != sup.get('goal_id') or snapshot.get('action_status') != 2:
        return False,'ACTION_GOAL_NOT_EXECUTING'
    ticks=snapshot.get('clock_ticks',[])
    if len(ticks)<2 or ticks[-1]<=ticks[0]:
        return False,'CLOCK_NOT_ADVANCING'
    return True,'LIVE_SAME_SESSION_MOTION_CANDIDATE_ONLY'


def capture(*, seconds=5.0):
    """Live graph and topic check, never publishes motion; returns read-only data."""
    import rclpy
    from geometry_msgs.msg import Twist
    from nav_msgs.msg import Odometry
    from rosgraph_msgs.msg import Clock
    from sensor_msgs.msg import LaserScan
    from std_msgs.msg import String
    from action_msgs.msg import GoalStatusArray
    from rclpy.qos import qos_profile_sensor_data, QoSProfile, QoSDurabilityPolicy, QoSReliabilityPolicy
    from rclpy.node import Node
    rclpy.init()
    node=Node('axia_p2_fault_admission_readonly')
    sample={'clock_ticks':[], 'graph':{}}
    def keep(k,v):
        sample[k]=v;sample[k+'_at']=time.monotonic()
    def status(k,msg):
        try:keep(k,json.loads(msg.data))
        except (ValueError,TypeError):keep(k,{'invalid':True})
    def clock(m):
        stamp=int(m.clock.sec)*1_000_000_000+int(m.clock.nanosec)
        keep('clock',stamp)
        if not sample['clock_ticks'] or sample['clock_ticks'][-1]!=stamp:
            sample['clock_ticks']=(sample['clock_ticks']+[stamp])[-5:]
    def action(m):
        for z in m.status_list:
            if z.status==2:
                keep('action',2)
                sample['action_status']=z.status
                sample['action_goal_uuid']=bytes(z.goal_info.goal_id.uuid).hex()
                break
    # ROS action status is transition-based; a late subscriber MUST request
    # the durable retained EXECUTING sample, not wait for a periodic heartbeat.
    action_qos=QoSProfile(depth=10)
    action_qos.reliability=QoSReliabilityPolicy.RELIABLE
    action_qos.durability=QoSDurabilityPolicy.TRANSIENT_LOCAL
    subs=[
      node.create_subscription(Odometry,'/odom',lambda m: (keep('odom',1),sample.__setitem__('odom_v',m.twist.twist.linear.x)),qos_profile_sensor_data),
      node.create_subscription(Twist,'/cmd_vel',lambda m:(keep('final_cmd',1),sample.__setitem__('cmd_v',m.linear.x)),10),
      node.create_subscription(Twist,'/cmd_vel_pre_guard',lambda m:(keep('pre_guard_cmd',1),sample.__setitem__('pre_guard_v',m.linear.x)),10),
      node.create_subscription(LaserScan,'/scan',lambda m:keep('scan',1),qos_profile_sensor_data),
      node.create_subscription(Clock,'/clock',clock,qos_profile_sensor_data),
      node.create_subscription(String,'/axia/p2/base_guard',lambda m:status('guard',m),10),
      node.create_subscription(String,'/axia/safety/state',lambda m:status('supervisor',m),10),
      node.create_subscription(GoalStatusArray,'/navigate_to_pose/_action/status',action,action_qos),
    ]
    try:
        deadline=time.monotonic()+seconds
        reason='NO_SAMPLES'
        while time.monotonic()<deadline:
            rclpy.spin_once(node,timeout_sec=.1)
            for topic in ('/cmd_vel','/cmd_vel_pre_guard','/cmd_vel_supervised'):
                sample['graph'][topic]=[(z.node_name,z.topic_type)
                    for z in node.get_publishers_info_by_topic(topic)]
            ok,reason=assess(sample,now=time.monotonic())
            if ok:return True,reason,sample
        return False,reason,sample
    finally:
        for s in subs:node.destroy_subscription(s)
        node.destroy_node()
        rclpy.shutdown()
