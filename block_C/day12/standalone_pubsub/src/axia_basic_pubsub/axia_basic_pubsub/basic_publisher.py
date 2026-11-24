import rclpy
from rclpy.node import Node
from rclpy.executors import ExternalShutdownException
from std_msgs.msg import String


class BasicPublisher(Node):
    def __init__(self):
        super().__init__('basic_publisher')
        self.publisher = self.create_publisher(String, '/axia/basic/chatter', 10)
        self.count = 0
        self.timer = self.create_timer(1.0, self.timer_callback)

    def timer_callback(self):
        self.count += 1
        msg = String()
        msg.data = f'Hello ROS 2: {self.count}'
        self.publisher.publish(msg)
        self.get_logger().info(f'PUB: {msg.data}')


def main(args=None):
    rclpy.init(args=args)
    node = BasicPublisher()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()
