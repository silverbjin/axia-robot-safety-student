from setuptools import setup
package_name = 'axia_fault_injector'
setup(name=package_name, version='0.1.0',
      packages=[package_name],
      data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
      ],
      install_requires=['setuptools'], zip_safe=True,
      maintainer='AXIA Safety Instructor',
      maintainer_email='noreply@example.invalid',
      description='Controlled educational LaserScan fault injection, no E-Stop',
      license='Apache-2.0', tests_require=['pytest'],
      entry_points={'console_scripts': [
          'fault_injector_node = axia_fault_injector.fault_injector_node:main'
      ]})
