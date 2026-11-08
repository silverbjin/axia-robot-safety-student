"""Class-only synthetic state sender. Not a fault injector and not a control node.

For a dedicated ROS_DOMAIN_ID, after explicit opt-in, publish only a known
synthetic std_msgs/String state from the PUBLIC fixture. Never run with P1 live.
"""
import argparse
import json
import os
import sys
import time
from pathlib import Path


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--case', default='NORMAL_HEALTHY')
    parser.add_argument('--count', type=int, default=4)
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args(argv)
    fixture = Path(__file__).resolve().parent.parent / 'p1_states.jsonl'
    cases = [json.loads(x) for x in fixture.read_text().splitlines() if x.strip()]
    entry = next((x for x in cases if x['case_id'] == args.case), None)
    if entry is None or not 1 <= args.count <= 20:
        print('BLOCKED: unknown fixture or count outside [1,20]', file=sys.stderr)
        return 2
    print(f'SYNTHETIC_CASE={args.case} EXPECTED_LEVEL={entry["expected_level"]} '
          f'EXPECTED_MESSAGE={entry["expected_message"]}')
    if args.dry_run:
        print('DRY_RUN_ONLY; ROS_VERIFIED=NOT_RUN')
        return 0
    if os.environ.get('AXIA_D03_ISOLATED_SYNTHETIC_ONLY') != 'YES' or not (
        (os.environ.get('ROS_DOMAIN_ID') or '').isdigit() and
        1 <= int(os.environ['ROS_DOMAIN_ID']) <= 232
    ):
        print('BLOCKED: require AXIA_D03_ISOLATED_SYNTHETIC_ONLY=YES and nonzero '
              'ROS_DOMAIN_ID in isolated network', file=sys.stderr)
        return 2
    try:
        import rclpy
        from rclpy.node import Node
        from std_msgs.msg import String
    except ImportError:
        print('BLOCKED: Jazzy rclpy/std_msgs missing', file=sys.stderr)
        return 2
    rclpy.init()
    node = Node('axia_d03_synthetic_state_publisher')
    pub = node.create_publisher(String, '/axia/safety/state', 10)
    try:
        for i in range(args.count):
            msg = String()
            msg.data = json.dumps(entry['payload'])
            pub.publish(msg)
            rclpy.spin_once(node, timeout_sec=0.05)
            print(f'PUBLISHED_SYNTHETIC {args.case} iteration={i + 1}/{args.count}')
            time.sleep(0.25)
    finally:
        node.destroy_node()
        rclpy.shutdown()
    return 0


if __name__ == '__main__':
    sys.exit(main())