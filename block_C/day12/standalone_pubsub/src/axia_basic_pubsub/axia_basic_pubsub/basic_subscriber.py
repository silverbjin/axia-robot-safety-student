import rclpy
from rclpy.node import Node
from rclpy.executors import ExternalShutdownException
from std_msgs.msg import String


class BasicSubscriber(Node):
    def __init__(self):
        super().__init__('basic_subscriber')
        self.subscription = self.create_subscription(
            String, '/axia/basic/chatter', self.listener_callback, 10)

    def listener_callback(self, msg):
        self.get_logger().info(f'SUB: {msg.data}')


def main(args=None):
    rclpy.init(args=args)
    node = BasicSubscriber()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()
