import rclpy
from rclpy.node import Node
from rclpy.executors import ExternalShutdownException
from diagnostic_msgs.msg import DiagnosticArray

TOPIC = '/axia/education/diagnostics'
LEVEL_NAMES = {0: 'OK', 1: 'WARN', 2: 'ERROR', 3: 'STALE'}


def level_number(level):
    return level[0] if isinstance(level, bytes) else int(level)


class DiagnosticSubscriber(Node):
    def __init__(self):
        super().__init__('diagnostic_subscriber')
        self.count = 0
        self.subscription = self.create_subscription(
            DiagnosticArray, TOPIC, self.listener_callback, 10)
        self.get_logger().info('Waiting for diagnostic events')

    def listener_callback(self, msg):
        for status in msg.status:
            values = {item.key: item.value for item in status.values}
            self.count += 1
            level = LEVEL_NAMES.get(level_number(status.level), 'UNKNOWN')
            self.get_logger().info(
                f"SUB #{self.count} event={values.get('event_id', '?')} "
                f"level={level} model={values.get('model', '-')} "
                f"score={values.get('score', '-')} cutoff={values.get('cutoff', '-')}")


def main(args=None):
    rclpy.init(args=args)
    node = DiagnosticSubscriber()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()
