"""Nav2 P2-only parameter writer (official source and P1 values preserved)."""
from pathlib import Path
import hashlib
import logging
import os
import sys
import tempfile

import yaml

HERE = Path(__file__).resolve().parent
# The existing standalone source launch and new installed package share the
# SAME P2 YAML/tool implementations. Check a real file rather than assuming
# the current working directory or a fixed number of parent directories.
SOURCE_RUNTIME=HERE.parents[3]
TOOL_DIR=(SOURCE_RUNTIME / 'tools'
          if (SOURCE_RUNTIME / 'tools/p2_zone_overlay.py').is_file()
          else HERE.parent / 'tools')
sys.path.insert(0,str(TOOL_DIR))
from p2_zone_overlay import patch_p2_zone_parameters
from p2_g07_cm_stop_zero_delivery import apply_g07_zero_delivery
from p2_mvp_one_goal_oracle import DEMO_GOAL_TOLERANCE_M



def set_mvp_goal_tolerance(params):
    """Narrow XY tolerance ONLY in the explicitly approved single-Goal demo.

    Keep all official Nav2 plugins, speeds, behaviors, obstacle zones and
    regular P1/G07 startup untouched. Refuse an unknown goal-checker layout.
    """
    if not isinstance(params,dict):
        raise ValueError('MVP_NAV2_PARAMS_NOT_MAP')
    controller=params.get('controller_server',{}).get('ros__parameters')
    if not isinstance(controller,dict):
        raise ValueError('MVP_NAV2_CONTROLLER_PARAMS_MISSING')
    matched=[(k,v) for k,v in controller.items()
             if isinstance(v,dict) and 'xy_goal_tolerance' in v]
    if len(matched)!=1:
        raise ValueError('MVP_NAV2_GOAL_CHECKER_AMBIGUOUS')
    key,checker=matched[0]
    original=checker['xy_goal_tolerance']
    if type(original) not in (int,float) or not (0.05 <= original <= 0.5):
        raise ValueError('MVP_NAV2_GOAL_TOLERANCE_UNEXPECTED')
    checker['xy_goal_tolerance']=DEMO_GOAL_TOLERANCE_M
    logging.warning('AXIA_P2_MVP_GOAL_TOLERANCE_ONLY plugin=%s original=%s demo=%.3f',
                    key,original,DEMO_GOAL_TOLERANCE_M)
    return original


def apply_g07_task02_simple_tf_candidate(params, env):
    """One public simulation candidate; no fast-robot/hardware safety claim.

    Official Nav2 fast path is source->base without time-shift interpolation.
    A missing transform still invokes the official CM invalid-source STOP
    because source_timeout remains positive. Only a real limited-speed
    Gazebo CLEAR/SLOW/STOP + inter-node TTL run can accept this candidate.
    """
    if not isinstance(params,dict) or not isinstance(env,dict):
        raise ValueError("G07_TASK02_SIMPLE_TF_BAD_INPUT")
    if env.get("AXIA_G07_TASK02_SIMPLE_TF_CANDIDATE") != "1":
        return False
    # Same exact Gazebo simulation profile in real CI and manual Owner L3.
    # The Owner never borrows CI credentials; all Goal TTY/PID consent is
    # still independently enforced by p2_g07_ci_moving_goal.run().
    core=(env.get("AXIA_P0_SIM_ONLY")=="1"
          and env.get("AXIA_G07_OWNER_STARTUP_PARITY")=="1"
          and env.get("AXIA_P2_G07_PHYSICAL_PREFLIGHT")=="1")
    ci=(env.get("GITHUB_ACTIONS")=="true"
        and env.get("AXIA_G07_CI_SIM_GOAL_ALLOWED")=="1")
    owner=(env.get("GITHUB_ACTIONS")!="true"
           and env.get("AXIA_G07_CI_SIM_GOAL_ALLOWED")!="1"
           and env.get("AXIA_G07_TASK04_OWNER_MOVING_L3")=="1"
           and env.get("AXIA_P2_G07_RELOCATED_OBSTACLE")=="1")
    if not core or not (ci or owner):
        raise ValueError("G07_TASK02_SIMPLE_TF_SIM_ONLY_AUTHORITY_DENIED")
    cm=params.get("collision_monitor",{}).get("ros__parameters")
    if not isinstance(cm,dict):
        raise ValueError("G07_TASK02_SIMPLE_TF_CM_MISSING")
    polygons=cm.get("polygons")
    if not (type(cm.get("transform_tolerance")) in (int,float)
            and cm["transform_tolerance"]==0.2
            and cm.get("base_shift_correction") is True
            and type(cm.get("source_timeout")) in (int,float)
            and cm["source_timeout"]==1.0
            and type(cm.get("stop_pub_timeout")) in (int,float)
            and cm["stop_pub_timeout"]==5.0
            and cm.get("cmd_vel_in_topic")=="cmd_vel_supervised"
            and cm.get("cmd_vel_out_topic")=="cmd_vel_pre_guard"
            and isinstance(polygons,list) and len(polygons)>=2
            and polygons[:2]==["AXIA_StopFront","AXIA_SlowFront"]):
        raise ValueError("G07_TASK02_SIMPLE_TF_FROZEN_CM_SAFETY_CONTRACT_MISMATCH")
    cm["base_shift_correction"]=False
    return True


def write_p2_parameters(source):
    src = Path(source).expanduser().resolve(strict=True)
    raw = src.read_bytes()
    zones = (SOURCE_RUNTIME / 'configs/p2_collision_monitor_zones.yaml'
             if (SOURCE_RUNTIME / 'configs/p2_collision_monitor_zones.yaml').is_file()
             else HERE.parent / 'config/p2_collision_monitor_zones.yaml')
    if not zones.is_file():
        raise ValueError('P2_COLLISION_MONITOR_ZONE_CONFIG_NOT_INSTALLED')
    p = patch_p2_zone_parameters(yaml.safe_load(raw), yaml.safe_load(zones.read_text()))
    if os.environ.get('AXIA_P2_MVP_ONE_GOAL') == '1':
        set_mvp_goal_tolerance(p)
    cm = p['collision_monitor']['ros__parameters']
    if cm['cmd_vel_out_topic'] != 'cmd_vel':
        raise ValueError('P1 output contract unexpectedly changed')
    cm['cmd_vel_out_topic'] = 'cmd_vel_pre_guard'
    # Only for authorized G07 simulation, keep Nav2 CM STOP ZERO messages
    # continuous for the 1s odom dwell while the unchanged Guard retains
    # 0.15s upstream CM TTL. Never affect G05/G06 or ordinary P1/P2.
    if apply_g07_zero_delivery(cm, os.environ):
        logging.warning(
            'AXIA_G07_CM_STOP_ZERO_DELIVERY_WINDOW_SEC=%s '
            'GUARD_CM_TTL_UNCHANGED=0.15 SIMULATION_ONLY',
            cm['stop_pub_timeout'])

    if apply_g07_task02_simple_tf_candidate(p,dict(os.environ)):
        logging.warning(
            'AXIA_G07_TASK02_SIMPLE_TF_CANDIDATE base_shift_correction=false '
            'transform_tolerance=0.2 source_timeout=1.0 '
            'Guard_TTL=0.15 SIMULATION_ONLY_NOT_SAFETY_RELEASED')

    with tempfile.NamedTemporaryFile('w', prefix='axia_p2_nav2_', suffix='.yaml',
                                     encoding='utf-8', delete=False) as fp:
        yaml.safe_dump(p, fp, sort_keys=False)
        output = fp.name
    logging.warning('P2 CM output only remapped to guarded input; SOURCE_SHA256=%s ZONES_SHA256=%s OUT=%s',
                    hashlib.sha256(raw).hexdigest(),
                    hashlib.sha256(zones.read_bytes()).hexdigest(), output)
    return output
