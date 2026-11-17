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


def apply_g07_task02_tf_wait_candidate(params, env):
    """Single sim-only opt-in: bound official Advanced TF wait to 20ms.

    Source invalidity still produces STOP because official Nav2 CM sees
    positive source_timeout. This may cause extra STOPs; only actual
    CLEAR/SLOW/STOP + TTL evidence can qualify the candidate for a demo.
    Do not disable base_shift_correction or extend safety time budgets.
    """
    if not isinstance(params, dict) or not isinstance(env, dict):
        raise ValueError('G07_TASK02_BAD_INPUT')
    if env.get('AXIA_G07_TASK02_TF_WAIT_CANDIDATE') != '1':
        return False
    required = {'GITHUB_ACTIONS': 'true', 'AXIA_P0_SIM_ONLY': '1',
                'AXIA_G07_CI_SIM_GOAL_ALLOWED': '1',
                'AXIA_G07_OWNER_STARTUP_PARITY': '1'}
    if any(env.get(key) != val for key,val in required.items()):
        raise ValueError('G07_TASK02_PUBLIC_SIM_AUTHORITY_INVALID')
    cm = params.get('collision_monitor', {}).get('ros__parameters')
    if not isinstance(cm, dict):
        raise ValueError('G07_TASK02_CM_PARAMS_ABSENT')
    if not (type(cm.get('transform_tolerance')) in (float, int)
            and cm['transform_tolerance'] == 0.2
            and cm.get('base_shift_correction') is True
            and type(cm.get('source_timeout')) in (float,int)
            and cm['source_timeout'] == 1.0
            and type(cm.get('stop_pub_timeout')) in (float,int)
            and cm['stop_pub_timeout'] == 5.0
            and cm.get('cmd_vel_in_topic') == 'cmd_vel_supervised'
            and cm.get('cmd_vel_out_topic') == 'cmd_vel_pre_guard'):
        raise ValueError('G07_TASK02_OFFICIAL_CM_SAFE_CONTRACT_NOT_MATCHED')
    cm['transform_tolerance'] = 0.02
    return True


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

    if apply_g07_task02_tf_wait_candidate(p, dict(os.environ)):
        logging.warning(
            'AXIA_G07_TASK02_CM_ADVANCED_TF_WAIT=0.02 '
            'BASE_SHIFT_CORRECTION=true SOURCE_TIMEOUT=1.0 '
            'GUARD_CM_TTL=0.15 SIMULATION_ONLY_NOT_RELEASED')

    with tempfile.NamedTemporaryFile('w', prefix='axia_p2_nav2_', suffix='.yaml',
                                     encoding='utf-8', delete=False) as fp:
        yaml.safe_dump(p, fp, sort_keys=False)
        output = fp.name
    logging.warning('P2 CM output only remapped to guarded input; SOURCE_SHA256=%s ZONES_SHA256=%s OUT=%s',
                    hashlib.sha256(raw).hexdigest(),
                    hashlib.sha256(zones.read_bytes()).hexdigest(), output)
    return output
