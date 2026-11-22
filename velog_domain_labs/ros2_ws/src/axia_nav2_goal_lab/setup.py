from setuptools import setup
name="axia_nav2_goal_lab"
setup(name=name,version="0.1.0",packages=[name],data_files=[("share/ament_index/resource_index/packages",["resource/"+name]),("share/"+name,["package.xml"])],install_requires=["setuptools"],zip_safe=True,description="AXIA domain lab 03",license="Apache-2.0",entry_points={"console_scripts":[name+"_demo = "+name+".__main__:main"]})
