"""Student-only ament packaging of the already-reviewed AXIA P1 launch files.

No Nav2/TurtleBot3 source code copied or modified.
"""
from glob import glob
from setuptools import setup

package_name = 'axia_safety_bringup'
setup(
    name=package_name, version='0.1.0', packages=[],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', glob('launch/*.py')),
    ],
    install_requires=['setuptools'], zip_safe=True,
    maintainer='AXIA Safety Student', maintainer_email='noreply@example.invalid',
    description='AXIA source P1 launch overlay for Jazzy classroom simulation',
    license='Apache-2.0',
)
