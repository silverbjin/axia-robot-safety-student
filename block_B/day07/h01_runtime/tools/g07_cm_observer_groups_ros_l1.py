#!/usr/bin/env python3
"""Real Jazzy rclpy two-PROCESS L1 diagnostic A/B — NO robot/Goal/Gazebo.

The publisher is in an independent OS process (like official CM); a single
synthetic String subscriber in the observer's DEFAULT callback group blocks
for 240ms exactly while both read-only Twist topics continue publishing.
The original DEFAULT CM group must exhibit callback starvation; the
two distinct MutuallyExclusiveCallbackGroups are the proposed local change.
Every result is diagnostic-only. Source timing/received RMW timing recorded.
"""
import json
import subprocess
import sys
import threading
import time
from p2_g07_observer_cb_group_policy import scoped_cm_groups

ROOT="/axia_test_g07_cm_observer_group_l1"


def synthetic_publisher(mode):
    import rclpy
    from rclpy.node import Node
    from geometry_msgs.msg import Twist
    from std_msgs.msg import String
    rclpy.init()
    n=Node("axia_g07_cm_l1_independent_publisher_"+mode)
    topic=ROOT+"/"+mode
    pub_cm=n.create_publisher(Twist,topic+"/cm",10)
    pub_sup=n.create_publisher(Twist,topic+"/supervised",10)
    pub_block=n.create_publisher(String,topic+"/block_default",10)
    deadline=time.monotonic()+10
    while (time.monotonic()<deadline and
           not (pub_cm.get_subscription_count()>=2 and
                pub_sup.get_subscription_count()>=2 and
                pub_block.get_subscription_count()>=1)):
        time.sleep(.05)
    ready=(pub_cm.get_subscription_count()>=2 and
           pub_sup.get_subscription_count()>=2 and
           pub_block.get_subscription_count()>=1)
    send=[]
    if ready:
        msg=Twist()
        for i in range(75):
            msg.angular.z=float(i)  # an exact small sequence integer
            send.append((time.monotonic(),i))
            pub_cm.publish(msg)
            pub_sup.publish(msg)
            if i==15:
                pub_block.publish(String(data="HOLD_DEFAULT_CALLBACK_GROUP_240MS"))
            time.sleep(.040)
        time.sleep(.35)
    n.destroy_node()
    rclpy.try_shutdown()
    print(json.dumps(dict(status="READY" if ready else "PUBLISHER_DISCOVERY_HOLD",
                          sent=send,source_process_independent=True)),flush=True)
    return 0 if ready else 3


def independent_witness(mode):
    """Same exact test topics, DIFFERENT ROS node/OS process and executor."""
    import rclpy
    from rclpy.node import Node
    from geometry_msgs.msg import Twist
    rclpy.init()
    node=Node("axia_g07_cm_l1_independent_witness_"+mode)
    data={"cm":[],"supervised":[]}
    topic=ROOT+"/"+mode
    for kind in ("cm","supervised"):
        node.create_subscription(Twist,topic+"/"+kind,
             lambda msg,info,k=kind:data[k].append((time.monotonic(),int(msg.angular.z))),10)
    deadline=time.monotonic()+7
    while time.monotonic()<deadline:
        rclpy.spin_once(node,timeout_sec=.08)
    node.destroy_node()
    rclpy.try_shutdown()
    def mx(rows):
        return round(max(((b[0]-a[0])*1000 for a,b in zip(rows,rows[1:])),
                         default=0),6)
    print(json.dumps(dict(status="WITNESS_READ_ONLY_FINISHED",
                          counts={key:len(v) for key,v in data.items()},
                          max_receive_gap_ms={key:mx(v) for key,v in data.items()},
                          distinct_sequences={key:len(set(x[1] for x in v))
                                              for key,v in data.items()},
                          independent_os_process=True)),flush=True)
    return 0


def measure(Node,MultiThreadedExecutor,SingleThreadedExecutor,MutuallyExclusiveCallbackGroup,
            Twist,String,mode):
    node=Node("axia_g07_cm_observer_l1_"+mode)
    cm_group,sup_group=scoped_cm_groups({
        "AXIA_G07_OWNER_STARTUP_PARITY":"1",
        "AXIA_G07_CM_OBSERVER_GROUPS":"1" if mode=="isolated" else "0",
    },MutuallyExclusiveCallbackGroup)
    topic=ROOT+"/"+mode
    data={"cm":[],"supervised":[]}
    lock=threading.Lock()
    blocked=threading.Event()
    def on_speed(name,msg,info):
        t=time.monotonic()
        seq=int(msg.angular.z)
        received=getattr(info,"received_timestamp",None)
        source=getattr(info,"source_timestamp",None)
        with lock:
            data[name].append((t,seq,received,source))
    for name,group in (("cm",cm_group),("supervised",sup_group)):
        kw={"callback_group":group} if group is not None else {}
        node.create_subscription(Twist,topic+"/"+name,
            lambda m,info,k=name:on_speed(k,m,info),10,**kw)

    def block_default(_):
        blocked.set()
        if mode in ("baseline","isolated"):
            time.sleep(.240)
    node.create_subscription(String,topic+"/block_default",block_default,10)
    executor=(SingleThreadedExecutor() if mode=="single_unblocked" else
              MultiThreadedExecutor(num_threads=2))
    executor.add_node(node)
    worker=threading.Thread(target=executor.spin,daemon=True)
    worker.start()
    publisher={}
    start=time.monotonic()
    try:
        witness=subprocess.Popen([sys.executable,__file__,"--witness",mode],
                stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        time.sleep(.2)
        proc=subprocess.run([sys.executable,__file__,"--publisher",mode],
                capture_output=True,text=True,timeout=30)
        if proc.returncode==0:
            try:publisher=json.loads(proc.stdout.strip().splitlines()[-1])
            except (ValueError,IndexError):publisher={}
        time.sleep(.25)
        try:
            witout,_=witness.communicate(timeout=12)
            witness_result=json.loads(witout.strip().splitlines()[-1])
        except (subprocess.TimeoutExpired,ValueError,IndexError):
            witness.kill()
            witness.communicate()
            witness_result={"status":"WITNESS_UNVERIFIED_HOLD"}
    except subprocess.TimeoutExpired:
        publisher={"status":"PUBLISHER_PROCESS_TIMEOUT"}
    finally:
        executor.shutdown(timeout_sec=3)
        worker.join(timeout=3)
        node.destroy_node()
    witness_result=locals().get("witness_result",{"status":"WITNESS_NOT_RUN_HOLD"})
    send=publisher.get("sent",[])
    sent={int(seq):float(t) for t,seq in send
          if isinstance(seq,int) and isinstance(t,(int,float))}
    def gaps(times):
        return max(((b-a)*1000 for a,b in zip(times,times[1:])),default=None)
    def matched(name):
        records=[row for row in data[name] if row[1] in sent]
        pairs=[]
        for (a,seq0,rx0,src0),(b,seq1,rx1,src1) in zip(records,records[1:]):
            d={"previous_seq":seq0,"current_seq":seq1,
               "callback_gap_ms":round((b-a)*1000,6),
               "publisher_gap_ms":round((sent[seq1]-sent[seq0])*1000,6)}
            if all(type(x) is int and x>0 for x in (rx0,rx1)):
                d["rmw_received_gap_ms"]=round((rx1-rx0)/1e6,6)
            if all(type(x) is int and x>0 for x in (src0,src1)):
                d["rmw_source_gap_ms"]=round((src1-src0)/1e6,6)
            pairs.append(d)
        return sorted(pairs,key=lambda row:row["callback_gap_ms"])[-3:]
    return {
        "mode":mode,"independent_publisher_status":publisher.get("status"),
        "independent_witness":witness_result,
        "source_process_independent":publisher.get("source_process_independent"),
        "default_group_blocker_executed":blocked.is_set(),
        "publisher_count":len(send),
        "publisher_max_gap_ms":round(gaps([t for t,_ in send]),6) if len(send)>1 else None,
        "cm_count":len(data["cm"]),"supervised_count":len(data["supervised"]),
        "cm_observer_max_gap_ms":round(gaps([row[0] for row in data["cm"]]),6)
          if len(data["cm"])>1 else None,
        "supervised_observer_max_gap_ms":round(gaps([row[0] for row in data["supervised"]]),6)
          if len(data["supervised"])>1 else None,
        "cm_worst_callback_pairs":matched("cm"),
        "supervised_worst_callback_pairs":matched("supervised"),
        "elapsed_sec":round(time.monotonic()-start,6)}


def main():
    if len(sys.argv)==3 and sys.argv[1]=="--publisher" and sys.argv[2] in ("baseline","isolated","multi_unblocked","single_unblocked"):
        return synthetic_publisher(sys.argv[2])
    if len(sys.argv)==3 and sys.argv[1]=="--witness" and sys.argv[2] in ("baseline","isolated","multi_unblocked","single_unblocked"):
        return independent_witness(sys.argv[2])
    if len(sys.argv)!=1:
        return 3
    import rclpy
    from rclpy.node import Node
    from rclpy.executors import MultiThreadedExecutor, SingleThreadedExecutor
    from rclpy.callback_groups import MutuallyExclusiveCallbackGroup
    from geometry_msgs.msg import Twist
    from std_msgs.msg import String
    rclpy.init()
    try:
        single_ab=(len(sys.argv)==2 and sys.argv[1]=="--multi-v-single")
        base=measure(Node,MultiThreadedExecutor,SingleThreadedExecutor,
                     MutuallyExclusiveCallbackGroup,Twist,String,
                     "multi_unblocked" if single_ab else "baseline")
        candidate=measure(Node,MultiThreadedExecutor,SingleThreadedExecutor,
                          MutuallyExclusiveCallbackGroup,Twist,String,
                          "single_unblocked" if single_ab else "isolated")
    finally:
        rclpy.try_shutdown()
    nums=[base.get("cm_observer_max_gap_ms"),candidate.get("cm_observer_max_gap_ms"),
          candidate.get("supervised_observer_max_gap_ms")]
    source_stable=(all(isinstance(x,(float,int)) for x in
                       (base.get("publisher_max_gap_ms"),
                        candidate.get("publisher_max_gap_ms")))
                   and base["publisher_max_gap_ms"]<120
                   and candidate["publisher_max_gap_ms"]<120)
    w=candidate.get("independent_witness",{})
    witness_stable=(w.get("status")=="WITNESS_READ_ONLY_FINISHED"
                    and all(w.get("counts",{}).get(k,0)>=60
                            and w.get("max_receive_gap_ms",{}).get(k,999)<=120
                            for k in ("cm","supervised")))
    ok=(source_stable and witness_stable
        and all(isinstance(x,(int,float)) for x in nums)
        and base["default_group_blocker_executed"]
        and candidate["default_group_blocker_executed"]
        and min(base["cm_count"],candidate["cm_count"],
                candidate["supervised_count"])>=35
        and base["cm_observer_max_gap_ms"]>=180
        and candidate["cm_observer_max_gap_ms"]<=120
        and candidate["supervised_observer_max_gap_ms"]<=120)
    if single_ab:
        # A/B after removing the artificial 240ms callback: compare
        # actual ROS2 executor implementations, not the application logic.
        ok=(source_stable and witness_stable
            and candidate["cm_count"]>=65
            and candidate["supervised_count"]>=65
            and candidate["cm_observer_max_gap_ms"] is not None
            and candidate["supervised_observer_max_gap_ms"] is not None
            and candidate["cm_observer_max_gap_ms"]<=120
            and candidate["supervised_observer_max_gap_ms"]<=120)
    out=dict(schema="axia.g07.cm_observer_callback_group_ros_l1.v2",
             baseline=base,candidate=candidate,
             status=(("JAZZY_SINGLE_EXECUTOR_L1_CANDIDATE_PASS_NO_GOAL"
                      if single_ab else "SYNTHETIC_JAZZY_TWO_PROCESS_CALLBACK_GROUP_L1_PASS") if ok
                     else ("JAZZY_SINGLE_EXECUTOR_L1_HOLD" if single_ab
                           else "SYNTHETIC_JAZZY_TWO_PROCESS_CALLBACK_GROUP_L1_HOLD")),
             independent_publisher_source_stable=bool(source_stable),
             independent_witness_receive_stable=bool(witness_stable),
             root_cause_proven=False,actual_gazebo=False,actual_goal=False,
             wsl2_nvidia_root_cause_proven=False,certified_estop=False)
    print(("AXIA_G07_CM_EXECUTOR_SINGLE_AB_ROS_L1 " if single_ab else "AXIA_G07_CM_OBSERVER_GROUP_ROS_L1 ")+json.dumps(out,sort_keys=True),flush=True)
    return 0 if ok else 3

if __name__=="__main__":
    raise SystemExit(main())
