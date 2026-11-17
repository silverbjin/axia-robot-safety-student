from setuptools import setup
name = "axia_scenario_verifier"
setup(name=name, version="0.1.0", packages=[name],
      data_files=[("share/ament_index/resource_index/packages", ["resource/"+name]),
                  ("share/"+name, ["package.xml"])],
      install_requires=["setuptools"], zip_safe=True,
      maintainer="AXIA Safety Instructor", maintainer_email="noreply@example.invalid",
      description="P1 unit/fake ROS evidence orchestration, not certified safety",
      license="Apache-2.0", tests_require=["pytest"],
      entry_points={"console_scripts": [
          "p1_evidence_runner = axia_scenario_verifier.runner:main"
      ]})
