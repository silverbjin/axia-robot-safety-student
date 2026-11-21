#!/usr/bin/env python3
"""Real Jazzy rclpy L1 scheduling A/B, NO Gazebo, NO actual robot topics.

A controlled 240ms default-group callback stall is deliberately introduced
on this synthetic test node. We verify that its read-only Twist subscribers
share default-group serialization (RED-like baseline) but can keep 120ms
callback delivery under two independent MutuallyExclusiveCallbackGroups.
This is NOT proof of the NVIDIA WSL2 underlying scheduling root or hardware.
"""
import json
import os
import threading
import time
from p2_g07_observer_cb_group_policy import scoped_cm_groups

TOPIC_ROOT="/axia_test_g07_cm_observer_group_l1"


def measure(rclpy, Node, MultiThreadedExecutor, String, Twist, MutuallyExclusiveCallbackGroup,
            mode):
    node=Node("axia_g07_cm_observer_l1_"+mode)
    pubnode=Node("axia_g07_cm_synthetic_publisher_"+mode)
    groups=scoped_cm_groups({
        "AXIA_G07_OWNER_STARTUP_PARITY":"1",
        "AXIA_G07_CM_OBSERVER_GROUPS":"1" if mode=="isolated" else "0",
    },MutuallyExclusiveCallbackGroup)
    topic=TOPIC_ROOT+"/"+mode
    data={"cm":[],"supervised":[]}
    mutex=threading.Lock()
    def on_msg(name,msg):
        t=time.monotonic()
        with mutex:data[name].append((t,int(msg.angular.z)))
    subs=[]
    for name,group in zip(("cm","supervised"),groups):
        args={}
        if group is not None:
            args["callback_group"]=group
        subs.append(node.create_subscription(
            Twist,topic+"/"+name,lambda msg,n=name:on_msg(n,msg),10,**args))
    writers=[pubnode.create_publisher(Twist,topic+"/"+name,10)
             for name in ("cm","supervised")]
    blocked=threading.Event()
    def long_default_group_callback():
        # Strictly diagnostic: only a synthetic String subscriber/timer; no
        # actual safety ROS node, Gazebo topic, or publisher is accessed.
        blocked.set()
        time.sleep(.240)
        timer.cancel()
    timer=node.create_timer(.600,long_default_group_callback)
    ex=MultiThreadedExecutor(num_threads=2)
    ex.add_node(node)
    worker=threading.Thread(target=ex.spin,daemon=True)
    worker.start()
    msg=Twist()
    sent=[]
    started=time.monotonic()
    try:
        for i in range(70):
            msg.angular.z=float(i)
            sent.append((time.monotonic(),i))
            for pub in writers:pub.publish(msg)
            time.sleep(.040)
        time.sleep(.18)
    finally:
        ex.shutdown(timeout_sec=4)
        worker.join(timeout=4)
        node.destroy_node()
        pubnode.destroy_node()
    def maximum(values):
        return max(((b-a)*1000 for a,b in zip(values,values[1:])),default=None)
    sent_t=[t for t,_ in sent]
    cm_t=[t for t,_ in data["cm"]]
    sup_t=[t for t,_ in data["supervised"]]
    sent_by_seq={seq:t for t,seq in sent}
    def worst_callback_interval_vs_publisher(rows):
        # Join by explicit integer sequence, same process monotonic timebase.
        matched=[(t,seq) for t,seq in rows if seq in sent_by_seq]
        gaps=sorted(((t1-t0)*1000,(sent_by_seq[s1]-sent_by_seq[s0])*1000,
                    int(s0),int(s1))
                   for (t0,s0),(t1,s1) in zip(matched,matched[1:]))
        return [dict(callback_gap_ms=round(a,6),
                     publisher_gap_ms=round(b,6),
                     previous_seq=i,current_seq=j)
                for a,b,i,j in gaps[-3:]]
    return {
        "mode":mode,"blocked_callback_test_event_observed":blocked.is_set(),
        "cm_count":len(cm_t),"supervised_count":len(sup_t),
        "publisher_count":len(sent),
        "publisher_max_gap_ms":round(maximum(sent_t),6),
        "cm_worst_callback_pairs":worst_callback_interval_vs_publisher(data["cm"]),
        "supervised_worst_callback_pairs":worst_callback_interval_vs_publisher(data["supervised"]),
        "cm_observer_max_gap_ms":round(maximum(cm_t),6) if len(cm_t)>1 else None,
        "supervised_observer_max_gap_ms":(
            round(maximum(sup_t),6)
            if len(data["supervised"])>1 else None),
        "elapsed_sec":round(time.monotonic()-started,6)}


def main():
    import rclpy
    from rclpy.node import Node
    from rclpy.executors import MultiThreadedExecutor
    from rclpy.callback_groups import MutuallyExclusiveCallbackGroup
    from std_msgs.msg import String
    from geometry_msgs.msg import Twist
    rclpy.init()
    try:
        base=measure(rclpy,Node,MultiThreadedExecutor,String,Twist,
                     MutuallyExclusiveCallbackGroup,"baseline")
        candidate=measure(rclpy,Node,MultiThreadedExecutor,String,Twist,
                          MutuallyExclusiveCallbackGroup,"isolated")
    finally:
        rclpy.try_shutdown()
    limits=[base["cm_observer_max_gap_ms"],candidate["cm_observer_max_gap_ms"],
            candidate["supervised_observer_max_gap_ms"]]
    permitted=(all(isinstance(x,float) for x in limits)
               and base["blocked_callback_test_event_observed"]
               and candidate["blocked_callback_test_event_observed"]
               and base["cm_count"]>=25 and candidate["cm_count"]>=25
               and candidate["supervised_count"]>=25
               and base["cm_observer_max_gap_ms"]>=180
               and candidate["cm_observer_max_gap_ms"]<=120
               and candidate["supervised_observer_max_gap_ms"]<=120)
    output=dict(schema="axia.g07.cm_observer_callback_group_ros_l1.v1",
                baseline=base,candidate=candidate,status=(
                    "SYNTHETIC_JAZZY_RCLPY_GROUP_ISOLATION_L1_PASS"
                    if permitted else "SYNTHETIC_JAZZY_RCLPY_GROUP_ISOLATION_L1_HOLD"),
                actual_gazebo=False,actual_goal=False,
                wsl2_nvidia_cause_proven=False,certified_estop=False)
    print("AXIA_G07_CM_OBSERVER_GROUP_ROS_L1 "+
          json.dumps(output,sort_keys=True),flush=True)
    return 0 if permitted else 3

if __name__=="__main__":
    raise SystemExit(main())
