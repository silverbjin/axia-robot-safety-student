"""Install the existing P2 launch *and its exact policy helpers* for ros2 launch.

Never copy/mutate official ROS/Nav2 files, depth-enabled source Waffle, or
the runtime's authoritative P2 zone YAML. Relative sources are read once
by setuptools while building this ament_python package.
"""
from pathlib import Path
from setuptools import setup

name = "axia_safety_bringup"
here = Path(__file__).resolve().parent
runtime = here.parent.parent.parent
launch = sorted(str(p.relative_to(here)) for p in (here / "launch").glob("*.py"))
tool_names = (
    "p2_zone_overlay.py", "p2_g07_cm_stop_zero_delivery.py",
    "p2_mvp_one_goal_oracle.py",
)
def relative_to_setup(path):
    import os
    return os.path.relpath(path,here)

setup(
    name=name, version="0.1.0", packages=[name],
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + name]),
        ("share/" + name, ["package.xml"]),
        ("share/" + name + "/launch", launch),
        ("share/" + name + "/config",
         [relative_to_setup(runtime/"configs/p2_collision_monitor_zones.yaml")]),
        ("share/" + name + "/tools",
         [relative_to_setup(runtime/"tools"/tool) for tool in tool_names]),
    ],
    install_requires=["setuptools"], zip_safe=True,
    maintainer="AXIA Safety Instructor",maintainer_email="noreply@example.invalid",
    description="AXIA G07 installed thin Nav2 bringup (no new safety algorithm)",
    license="Apache-2.0", tests_require=["pytest"],
)
