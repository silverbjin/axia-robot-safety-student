#!/usr/bin/env python3
"""Actual Jazzy P2 no-Goal graph/sensor observer; never publishes motion.

This is a L2 preflight only. It is not a G05/G06/G07 or certified E-Stop test.
"""
import argparse
import json
from pathlib import Path
import time

TOPICS = (
    ('/cmd_vel_smoothed', 'velocity_smoother', 'axia_safety_supervisor'),
    ('/cmd_vel_supervised', 'axia_safety_supervisor', 'collision_monitor'),
    ('/cmd_vel_pre_guard', 'collision_monitor', 'axia_base_command_guard'),
    ('/cmd_vel', 'axia_base_command_guard', None),
)
TWIST='geometry_msgs/msg/Twist'


def check_graph(snapshot):
    reasons=[]
    for topic, publisher, recipient in TOPICS:
        value=snapshot.get(topic)
        if not isinstance(value,dict):
            reasons.append('MISSING_TOPIC:'+topic)
            continue
        pubs=value.get('publishers',[])
        subs=value.get('subscriptions',[])
        if len(pubs)!=1 or pubs[0].get('name')!=publisher or pubs[0].get('type')!=TWIST:
            reasons.append('WRONG_PUBLISHER:'+topic)
        if recipient and not any(s.get('name')==recipient and s.get('type')==TWIST for s in subs):
            reasons.append('WRONG_SUBSCRIBER:'+topic)
    return reasons


def main(argv=None):
    p=argparse.ArgumentParser()
    p.add_argument('--timeout-sec',type=float,default=120.0)
    p.add_argument('--output',required=True)
    args=p.parse_args(argv)
    if not 0<args.timeout_sec<=240:
        raise SystemExit('invalid timeout')
    import rclpy
    from rclpy.node import Node
    from rclpy.qos import qos_profile_sensor_data
    from geometry_msgs.msg import Twist
    from nav_msgs.msg import Odometry
    from sensor_msgs.msg import LaserScan
    from rosgraph_msgs.msg import Clock
    from std_msgs.msg import String
    rclpy.init()
    node=Node('axia_p2_readonly_observer')
    watch={'clock':[], 'scan':0,'odom':0,'cmd_nonzero':0,'guard':None}
    def clock(m):
        ns=int(m.clock.sec)*1000000000+int(m.clock.nanosec)
        if not watch['clock'] or ns != watch['clock'][-1]:
            watch['clock'].append(ns)
            if len(watch['clock'])>3: watch['clock']=watch['clock'][-3:]
    def command(m):
        if any(abs(v)>1e-6 for v in [m.linear.x,m.linear.y,m.linear.z,
                                      m.angular.x,m.angular.y,m.angular.z]):
            watch['cmd_nonzero']+=1
    def guard(m):
        try:watch['guard']=json.loads(m.data)
        except (ValueError,TypeError):watch['guard']={'invalid':True}
    subs=[
        node.create_subscription(Clock,'/clock',clock,qos_profile_sensor_data),
        node.create_subscription(LaserScan,'/scan',lambda _:watch.__setitem__('scan',watch['scan']+1),qos_profile_sensor_data),
        node.create_subscription(Odometry,'/odom',lambda _:watch.__setitem__('odom',watch['odom']+1),qos_profile_sensor_data),
        node.create_subscription(Twist,'/cmd_vel',command,10),
        node.create_subscription(String,'/axia/p2/base_guard',guard,10),
    ]
    snapshot={}
    start=time.monotonic()
    try:
        while time.monotonic()-start<args.timeout_sec:
            rclpy.spin_once(node,timeout_sec=.2)
            for topic,_,_ in TOPICS:
                snapshot[topic]={
                    'publishers':[{'name':x.node_name,'type':x.topic_type} for x in node.get_publishers_info_by_topic(topic)],
                    'subscriptions':[{'name':x.node_name,'type':x.topic_type} for x in node.get_subscriptions_info_by_topic(topic)]}
            errors=check_graph(snapshot)
            if (not errors and len(watch['clock'])>=2 and watch['clock'][-1]>watch['clock'][0]
                and watch['scan']>0 and watch['odom']>0
                and watch['cmd_nonzero']==0 and isinstance(watch['guard'],dict)
                and watch['guard'].get('certified_estop') is False
                and watch['guard'].get('sim_only') is True):
                state='P2_NO_GOAL_READONLY_READY'
                break
        else:
            state='P2_NO_GOAL_BLOCKED'
        report={'status':state,'graph':snapshot,'graph_reasons':check_graph(snapshot),
                'observations':watch,'goal_sent':False,'fault_injected':False,
                'gate_accepted':False,'certified_estop':False,'verification':'L2_NO_GOAL_ONLY'}
        out=Path(args.output);out.parent.mkdir(parents=True,exist_ok=True)
        with out.open('x') as fp:
            json.dump(report,fp,indent=2,ensure_ascii=False)
            fp.write('\n')
        print(state,flush=True)
        return 0 if state=='P2_NO_GOAL_READONLY_READY' else 2
    finally:
        for s in subs: node.destroy_subscription(s)
        node.destroy_node()
        rclpy.shutdown()


if __name__=='__main__':
    raise SystemExit(main())
