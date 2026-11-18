"""Regression from Owner screenshot and d04-gazebo-2GH7zxgm evidence.

Original failure 1: D05 world SceneBroadcaster wrapped by xacro:unless(headless).
Original failure 2: RViz cannot resolve 4 NAV2 meshes in /robot_description.
No ROS/Gazebo used by this L0 test. Do not infer WSLg pixel acceptance.
"""
from pathlib import Path
import importlib.util
import xml.etree.ElementTree as ET
import pytest

ROOT=Path(__file__).resolve().parents[3]
SCENE=ROOT/"block_B/day05/gazebo_live/prepare_scene.py"
VIEW=ROOT/"block_B/day08/live/prepare_rviz_mesh_view.py"
LAUNCH=ROOT/"block_B/day08/run_d08_student_live_once.sh"
CI=ROOT/".github/workflows/d08-student-gazebo-rviz-l2.yml"
X="{http://www.ros.org/wiki/xacro}"

def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def raw_world():
    return ET.fromstring("""<sdf xmlns:xacro="http://www.ros.org/wiki/xacro" version="1.6"><world name="default">
       <plugin filename="gz-sim-physics-system" name="gz::sim::systems::Physics"/>
       <xacro:unless value="$(arg headless)"><plugin filename="gz-sim-scene-broadcaster-system" name="gz::sim::systems::SceneBroadcaster"/></xacro:unless>
       <plugin filename="gz-sim-sensors-system" name="gz::sim::systems::Sensors"/>
    </world></sdf>""")

def test_d05_scene_broadcaster_from_d07_h01_owner_fix():
    mod=load(SCENE,"d08_scene_fix")
    root=raw_world()
    mod.ensure_scene_broadcaster_visible(root)
    world=root.find("world")
    matches=[x for x in world.findall("plugin") if x.get("name")=="gz::sim::systems::SceneBroadcaster"]
    assert len(matches)==1
    assert matches[0].get("filename")=="gz-sim-scene-broadcaster-system"
    assert not any("SceneBroadcaster" in ET.tostring(x,encoding="unicode")
                   for x in world.findall(X+"unless"))

def test_d05_scene_broadcaster_fails_closed_on_duplicate_or_missing():
    mod=load(SCENE,"d08_scene_fix2")
    root=raw_world()
    mod.ensure_scene_broadcaster_visible(root)
    with pytest.raises(ValueError):
        mod.ensure_scene_broadcaster_visible(root)
    other=raw_world()
    other.find("world").remove(other.find(".//"+X+"unless"))
    with pytest.raises(ValueError):
        mod.ensure_scene_broadcaster_visible(other)

def test_rviz_uses_official_installed_meshes_from_isolated_file(tmp_path):
    mod=load(VIEW,"d08_mesh_fix")
    prefix=tmp_path/"install"
    mesh_dir=prefix/"share/nav2_minimal_tb3_sim/models/turtlebot3_model/meshes"
    mesh_dir.mkdir(parents=True)
    for name in ("waffle_base.dae","lds.dae","r200.dae","tire.dae"):
        (mesh_dir/name).write_text("fixture")
    urdf=tmp_path/"turtlebot3_waffle.urdf"
    urdf.write_text('<robot name="waffle"><link name="base_link"><visual><geometry><mesh filename="package://nav2_minimal_tb3_sim/models/waffle_base.dae"/></geometry></visual></link></robot>')
    rviz=tmp_path/"original.rviz"
    rviz.write_text("  Displays:\n    - Class: rviz_default_plugins/RobotModel\n      Description Source: Topic\n      Description Topic:\n        Value: /robot_description\n      Links:\n        All Links Enabled: true\n")
    out=tmp_path/"out"
    out.mkdir()
    result=mod.build_view(prefix,urdf,rviz,out)
    generated=(out/"d08_waffle_view.urdf").read_text()
    view=(out/"d08_render_view.rviz").read_text()
    assert "package://nav2_minimal_tb3_sim/models/turtlebot3_model/meshes/waffle_base.dae" in generated
    assert "Description Source: File" in view
    assert "Description File:" in view
    assert "/robot_description" not in view
    assert result["fixed_meshes"]>=1 and result["source_modified"] is False

def test_rviz_fails_closed_if_real_meshes_are_missing(tmp_path):
    mod=load(VIEW,"d08_mesh_fix2")
    prefix=tmp_path/"inst"
    prefix.mkdir()
    urdf=tmp_path/"waffle.urdf"
    urdf.write_text('<robot><mesh filename="package://nav2_minimal_tb3_sim/models/waffle_base.dae"/></robot>')
    rviz=tmp_path/"v.rviz"
    rviz.write_text("      Description Source: Topic\n      Description Topic:\n        Value: /robot_description\n      Links:\n")
    (tmp_path/"out").mkdir()
    with pytest.raises(ValueError):
        mod.build_view(prefix,urdf,rviz,tmp_path/"out")

def test_actual_d08_gui_uses_only_d08_readonly_mesh_source_and_scene_gate():
    code=LAUNCH.read_text()
    assert "prepare_rviz_mesh_view.py" in code
    assert "D08_RVIZ_OFFICIAL_MESH_VIEW_READY" in code
    assert "AXIA_D04_STUDENT_RVIZ_CONFIG" in code
    source=SCENE.read_text()
    assert "ensure_scene_broadcaster_visible" in source
    workflow=CI.read_text()
    assert "D08_GZ_SCENE_BROADCASTER_POSE_GATE_PASS" in workflow
    assert "D08_RVIZ_OFFICIAL_MESH_VIEW_READY" in workflow
    assert "D08_RVIZ_MESH_RESOURCE_ERRORS_NONE_PASS" in workflow
    for forbidden in ("send_goal(", "cmd_vel pub", "create_publisher("):
        assert forbidden not in code

def test_gui_starts_after_server_and_ci_nested_shell_parses():
    import subprocess
    source=(ROOT/"block_B/day04/run_student_gazebo_yolo_once.sh").read_text()
    wrapper=LAUNCH.read_text()
    assert "AXIA_D08_STAGED_GUI=1" in wrapper
    assert "AXIA_D08_STAGED_GUI" in source
    assert 'headless:=True' in source
    assert "D08_GAZEBO_WORLD_READY_BEFORE_GUI" in source
    assert "start_group gazebo_gui" in source
    assert source.index("D08_GAZEBO_WORLD_READY_BEFORE_GUI") < source.index("start_group gazebo_gui")
    workflow=CI.read_text()
    start=workflow.index("          xvfb-run -a")
    end=workflow.index("          ' || {",start)
    nested=workflow[start:end]+"          '\n"
    parsed=subprocess.run(["bash","-n"],input=nested,text=True,capture_output=True)
    assert parsed.returncode==0, parsed.stderr
    assert "AXIA_D08_GUI_BACKEND=software" in workflow
