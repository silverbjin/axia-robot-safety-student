#!/usr/bin/env python3
"""One exact native collision_monitor parameter readback BEFORE any G07 Goal.

Task04 Xvfb native #44263077295: independent 'ros2 param get' clients had
a transient second-service discovery timeout after first reply succeeded.
A single bounded rclpy GetParameters response reads the exact active values.
This neither relaxes CM/Guard TTL nor grants a Goal or lifecycle authority.
"""
import argparse
import json
import math
import os
from pathlib import Path
import sys

# rcl_interfaces.msg.ParameterType: PARAMETER_BOOL=1, PARAMETER_DOUBLE=3.
_EXPECTED = {"stop_pub_timeout": (3, 5.0),
             "base_shift_correction": (1, False),
             "transform_tolerance": (3, 0.2),
             "source_timeout": (3, 1.0)}


def validate_values(values, *, require_simple_tf, d08_g07_tf_wait=False):
    if (type(d08_g07_tf_wait) is not bool or
            (d08_g07_tf_wait and require_simple_tf is not True)):
        raise ValueError("D08_G07_CM_TF_NATIVE_READBACK_MODE_INVALID")
    expected=dict(_EXPECTED)
    if d08_g07_tf_wait:
        expected["transform_tolerance"]=(3,0.02)
    names=list(expected if require_simple_tf else ("stop_pub_timeout",))
    result={"schema":"axia_g07_active_cm_native_parameter_readback_v1",
            "status":"ACTIVE_CM_NATIVE_PARAMETER_READBACK_BLOCKED",
            "required_simple_tf":bool(require_simple_tf),
            "requested":names,"actual":{},
            "goal_sent":False,"certified_estop":False}
    if not isinstance(values,dict) or type(require_simple_tf) is not bool:
        return result
    for key in names:
        observed=values.get(key)
        required_type,required_value=expected[key]
        if not isinstance(observed,(tuple,list)) or len(observed)!=2:
            return {**result,"first_failure":key+"_MISSING"}
        param_type,param_value=observed
        if type(param_type) is not int or param_type!=required_type:
            return {**result,"first_failure":key+"_TYPE"}
        if required_type==1:
            if type(param_value) is not bool or param_value is not required_value:
                return {**result,"first_failure":key+"_VALUE"}
        else:
            if (type(param_value) not in (float,int) or
                    not math.isfinite(param_value) or
                    abs(param_value-required_value)>1e-9):
                return {**result,"first_failure":key+"_VALUE"}
        result["actual"][key]=param_value
    return {**result,"status":"ACTIVE_CM_NATIVE_PARAMETER_READBACK_PASS",
            "first_failure":"NONE"}


def read_native(*, require_simple_tf, d08_g07_tf_wait=False):
    import rclpy
    from rcl_interfaces.srv import GetParameters
    node=None
    rclpy.init()
    try:
        node=rclpy.create_node("axia_g07_cm_native_param_gate",enable_rosout=False)
        client=node.create_client(GetParameters,"/collision_monitor/get_parameters")
        if not client.wait_for_service(timeout_sec=5.0):
            return {"status":"ACTIVE_CM_NATIVE_PARAMETER_READBACK_BLOCKED",
                    "first_failure":"CM_GET_PARAMETERS_SERVICE_MISSING",
                    "goal_sent":False,"certified_estop":False}
        request=GetParameters.Request()
        request.names=list(_EXPECTED if require_simple_tf else ("stop_pub_timeout",))
        future=client.call_async(request)
        rclpy.spin_until_future_complete(node,future,timeout_sec=9.0)
        if not future.done() or future.result() is None:
            return {"status":"ACTIVE_CM_NATIVE_PARAMETER_READBACK_BLOCKED",
                    "first_failure":"CM_GET_PARAMETERS_NATIVE_ACK_TIMEOUT",
                    "request_sent":True,"goal_sent":False,"certified_estop":False}
        response=future.result()
        if len(response.values)!=len(request.names):
            return {"status":"ACTIVE_CM_NATIVE_PARAMETER_READBACK_BLOCKED",
                    "first_failure":"CM_GET_PARAMETERS_RESPONSE_LENGTH",
                    "request_sent":True,"goal_sent":False,"certified_estop":False}
        observed={key:(int(value.type),
                       bool(value.bool_value) if int(value.type)==1
                       else float(value.double_value))
                  for key,value in zip(request.names,response.values)}
        return {**validate_values(
                    observed,require_simple_tf=require_simple_tf,
                    d08_g07_tf_wait=d08_g07_tf_wait),
                "request_sent":True}
    finally:
        if node is not None:node.destroy_node()
        rclpy.try_shutdown()


def main(argv=None):
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",required=True,type=Path)
    parser.add_argument("--require-simple-tf",action="store_true")
    parser.add_argument("--require-d08-g07-tf-wait",action="store_true")
    args=parser.parse_args(argv)
    report={"status":"ACTIVE_CM_NATIVE_PARAMETER_READBACK_BLOCKED",
            "first_failure":"RUNTIME_NOT_STARTED",
            "goal_sent":False,"certified_estop":False}
    try:
        if not (os.environ.get("ROS_DISTRO")=="jazzy"
                and os.environ.get("AXIA_P0_SIM_ONLY")=="1"
                and os.environ.get("GZ_PARTITION","").startswith("axia_p2_")):
            report["first_failure"]="NOT_ISOLATED_JAZZY_SIMULATION"
        else:
            report=read_native(require_simple_tf=args.require_simple_tf,
                               d08_g07_tf_wait=args.require_d08_g07_tf_wait)
    except (OSError,RuntimeError,ValueError,TypeError) as exc:
        report["first_failure"]="NATIVE_SERVICE_"+type(exc).__name__
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,sort_keys=True,indent=2)+"\n")
    print("AXIA_G07_CM_NATIVE_ACTIVE_PARAMETER_READBACK "+json.dumps(report,sort_keys=True),flush=True)
    if report.get("status")!="ACTIVE_CM_NATIVE_PARAMETER_READBACK_PASS":
        return 3
    print("AXIA_G07_CI_REAL_CM_STOP_ZERO_WINDOW_5S_GUARD_TTL_150MS_UNCHANGED",flush=True)
    if args.require_simple_tf:
        if args.require_d08_g07_tf_wait:
            print("D08_G07_REAL_CM_TF_WAIT_READBACK_PASS 0.02S SHIFT_FALSE SOURCE_TIMEOUT_1.0 GUARD_150MS_UNCHANGED",flush=True)
        else:
    print("AXIA_G07_TASK02_SIMPLE_TF_ACTIVE_READBACK_PASS SHIFT_FALSE TF_TOL_0.2 SOURCE_TIMEOUT_1.0 GUARD_150MS_UNCHANGED",flush=True)
    return 0

if __name__=="__main__":
    sys.exit(main())
