from pathlib import Path

import rclpy
from rclpy.node import Node
from rclpy.executors import ExternalShutdownException
from diagnostic_msgs.msg import DiagnosticArray, DiagnosticStatus, KeyValue

from .events import JsonlReader, parse_event, diagnostic_fields

TOPIC = '/axia/education/diagnostics'
DEFAULT_PATH = str(Path.home() / 'axia_d12_pubsub_lab' / 'data' / 'events.jsonl')


def to_message(event, stamp):
    fields = diagnostic_fields(event)
    status = DiagnosticStatus()
    status.level = bytes([fields['level']])
    status.name = fields['name']
    status.message = fields['message']
    status.hardware_id = fields['hardware_id']
    status.values = [KeyValue(key=k, value=v) for k, v in fields['values'].items()]
    msg = DiagnosticArray()
    msg.header.stamp = stamp
    msg.status = [status]
    return msg


class DiagnosticPublisher(Node):
    def __init__(self):
        super().__init__('diagnostic_publisher')
        self.declare_parameter('event_file', DEFAULT_PATH)
        self.reader = JsonlReader(self.get_parameter('event_file').value)
        self.publisher = self.create_publisher(DiagnosticArray, TOPIC, 10)
        self.timer = self.create_timer(0.2, self.timer_callback)
        self.get_logger().info(f'Watching {self.reader.path}; waiting for a subscriber')

    def timer_callback(self):
        # Do not consume events before discovery in the classroom demo.
        if self.publisher.get_subscription_count() == 0:
            return
        try:
            lines = self.reader.poll(limit=10)
        except OSError as exc:
            self.get_logger().error(f'FILE ERROR: {exc}')
            return
        for line in lines:
            try:
                event = parse_event(line)
            except ValueError as exc:
                self.get_logger().warning(f'SKIP invalid JSON event: {exc}')
                continue
            msg = to_message(event, self.get_clock().now().to_msg())
            self.publisher.publish(msg)
            self.get_logger().info(f"PUB event={event['event_id']} level={event['level']}")


def main(args=None):
    rclpy.init(args=args)
    node = DiagnosticPublisher()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()
