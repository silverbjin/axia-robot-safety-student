from setuptools import setup

package_name = 'axia_json_diagnostics'
setup(
    name=package_name,
    version='0.1.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='AXIA lab',
    maintainer_email='lab@example.invalid',
    description='AXIA D12 standalone educational ROS 2 lab',
    license='Apache-2.0',
    entry_points={'console_scripts': [
            "diagnostic_publisher = axia_json_diagnostics.diagnostic_publisher:main",
            "diagnostic_subscriber = axia_json_diagnostics.diagnostic_subscriber:main",
            "emit_event = axia_json_diagnostics.emit_event:main",
    ]},
)
