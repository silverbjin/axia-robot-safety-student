"""Nav2 P2-only parameter writer (official source and P1 values preserved)."""
from pathlib import Path
import hashlib
import logging
import os
import sys
import tempfile

import yaml

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[3] / 'tools'))
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

def write_p2_parameters(source):
    src = Path(source).expanduser().resolve(strict=True)
    raw = src.read_bytes()
    zones = HERE.parents[3] / 'configs' / 'p2_collision_monitor_zones.yaml'
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

    with tempfile.NamedTemporaryFile('w', prefix='axia_p2_nav2_', suffix='.yaml',
                                     encoding='utf-8', delete=False) as fp:
        yaml.safe_dump(p, fp, sort_keys=False)
        output = fp.name
    logging.warning('P2 CM output only remapped to guarded input; SOURCE_SHA256=%s ZONES_SHA256=%s OUT=%s',
                    hashlib.sha256(raw).hexdigest(),
                    hashlib.sha256(zones.read_bytes()).hexdigest(), output)
    return output
