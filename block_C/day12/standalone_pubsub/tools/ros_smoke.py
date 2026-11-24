"""Real Jazzy smoke: separate console-script processes plus independent DDS observer."""
import json
import os
from pathlib import Path
import signal
import subprocess
import tempfile
import time

import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from diagnostic_msgs.msg import DiagnosticArray


def main():
    with tempfile.TemporaryDirectory(prefix='axia-d12-') as work:
        root = Path(work)
        event_file = root / 'events.jsonl'
        children = []
        logs = {}
        rclpy.init()
        observer = Node('d12_smoke_observer')
        basic, diagnostics = [], []
        observer.create_subscription(String, '/axia/basic/chatter', lambda m: basic.append(m.data), 10)

        def on_diagnostic(msg):
            for s in msg.status:
                level = s.level[0] if isinstance(s.level, bytes) else int(s.level)
                values = {x.key: x.value for x in s.values}
                diagnostics.append((values['event_id'], level, values['score'], values['cutoff']))

        observer.create_subscription(DiagnosticArray, '/axia/education/diagnostics', on_diagnostic, 10)

        def start(name, package, *args):
            path = root / (name + '.log')
            logs[name] = path
            with path.open('w') as log:
                child = subprocess.Popen(['ros2', 'run', package, name, *args], stdout=log,
                                         stderr=subprocess.STDOUT, start_new_session=True)
            children.append(child)

        def wait_for(predicate, timeout=25):
            deadline = time.monotonic() + timeout
            while time.monotonic() < deadline:
                if any(p.poll() is not None for p in children):
                    raise RuntimeError('node exited unexpectedly')
                rclpy.spin_once(observer, timeout_sec=0.1)
                if predicate():
                    return
            raise AssertionError('timed out waiting for DDS/console evidence')

        try:
            start('basic_subscriber', 'axia_basic_pubsub')
            start('basic_publisher', 'axia_basic_pubsub')
            start('diagnostic_subscriber', 'axia_json_diagnostics')
            start('diagnostic_publisher', 'axia_json_diagnostics', '--ros-args', '-p', f'event_file:={event_file}')
            topic = '/axia/education/diagnostics'
            wait_for(lambda: any(x.node_name == 'diagnostic_subscriber' for x in observer.get_subscriptions_info_by_topic(topic))
                     and observer.count_publishers(topic) == 1 and len(basic) >= 2)
            # File starts absent; emit all four levels after the actual subscriber is discovered.
            for i, label in enumerate(('OK', 'WARN', 'ERROR', 'STALE')):
                subprocess.run(['ros2', 'run', 'axia_json_diagnostics', 'emit_event', '--file', str(event_file),
                                '--id', f'E{i}', '--level', label, '--model', 'AE', '--score', '0.72',
                                '--cutoff', '0.5'], check=True, timeout=10)
            wait_for(lambda: len(diagnostics) >= 4 and all(f'event=E{i} level={label}' in logs['diagnostic_subscriber'].read_text()
                     for i, label in enumerate(('OK', 'WARN', 'ERROR', 'STALE'))))
            end = time.monotonic() + 1
            while time.monotonic() < end:
                rclpy.spin_once(observer, timeout_sec=0.1)
            assert diagnostics == [(f'E{i}', i, '0.72', '0.5') for i in range(4)], diagnostics
            assert all(x.startswith('Hello ROS 2: ') for x in basic)
            assert 'SUB: Hello ROS 2:' in logs['basic_subscriber'].read_text()
            assert observer.count_publishers('/cmd_vel') == 0
            assert observer.count_publishers('/axia/education/diagnostics') == 1
            print('D12_REAL_ROS_L1_PASS ' + json.dumps({'basic_count': len(basic), 'diagnostics': diagnostics,
                  'cmd_vel_publishers': 0, 'scope': 'education_only_no_gazebo_no_d11'}))
        finally:
            for p in children:
                if p.poll() is None:
                    os.killpg(p.pid, signal.SIGINT)
            for p in children:
                try:
                    p.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(p.pid, signal.SIGKILL)
                    p.wait(timeout=5)
            for name, path in logs.items():
                print(f'--- {name} ---\n{path.read_text()}')
            observer.destroy_node()
            rclpy.try_shutdown()


if __name__ == '__main__':
    main()
