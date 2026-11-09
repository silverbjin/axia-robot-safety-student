"""Fail-closed source-based launch adaptation of locally installed official Nav2 Jazzy.

Does not write to /opt/ros. Docking Server is outside P0 and must not own /cmd_vel.
"""
import ast
import hashlib
import logging
from pathlib import Path
import runpy


def drop_docking_from_navigation_source(source: str):
    tree = ast.parse(source)

    class Strip(ast.NodeTransformer):
        def __init__(self):
            self.dropped_nodes = 0
            self.dropped_lifecycle = 0

        def visit_Assign(self, node):
            if (len(node.targets) == 1
                    and isinstance(node.targets[0], ast.Name)
                    and node.targets[0].id == "lifecycle_nodes"):
                if not isinstance(node.value, ast.List):
                    raise ValueError("Nav2 lifecycle list changed shape")
                matches = [x for x in node.value.elts
                           if isinstance(x, ast.Constant) and x.value == "docking_server"]
                if len(matches) != 1:
                    raise ValueError("Nav2 DockingServer lifecycle entry missing or duplicate")
                node.value.elts = [x for x in node.value.elts if x not in matches]
                self.dropped_lifecycle += 1
            return self.generic_visit(node)

        def visit_List(self, node):
            elements = []
            for elt in node.elts:
                if (isinstance(elt, ast.Call)
                        and isinstance(elt.func, ast.Name)
                        and elt.func.id in {"Node", "ComposableNode"}):
                    names = [kw.value.value for kw in elt.keywords
                             if kw.arg == "name" and isinstance(kw.value, ast.Constant)]
                    if names == ["docking_server"]:
                        self.dropped_nodes += 1
                        continue
                elements.append(self.visit(elt))
            node.elts = elements
            return node

    visitor = Strip()
    tree = visitor.visit(tree)
    if visitor.dropped_nodes != 2 or visitor.dropped_lifecycle != 1:
        raise ValueError(
            "Nav2 upstream docking shape differs: "
            f"Node/ComposableNode={visitor.dropped_nodes}, lifecycle={visitor.dropped_lifecycle}"
        )
    if any(isinstance(node, ast.Constant) and node.value == "docking_server"
           for node in ast.walk(tree)):
        raise ValueError("Unremoved docking_server literal in official launch")
    return compile(ast.fix_missing_locations(tree), "nav2_navigation_p0_overlay", "exec")


def load_upstream_launch(path: Path, *, strip_docking=False):
    path = Path(path).resolve(strict=True)
    if path.name not in {"tb3_simulation_launch.py", "bringup_launch.py",
                         "navigation_launch.py"}:
        raise ValueError(f"Refusing unexpected official launcher: {path}")
    source = path.read_text(encoding="utf-8")
    digest = hashlib.sha256(source.encode("utf-8")).hexdigest()
    logging.warning("AXIA official Nav2 source %s SHA256=%s", path, digest)
    if strip_docking:
        if path.name != "navigation_launch.py":
            raise ValueError("Docking removal only accepted for navigation_launch.py")
        namespace = {"__name__": "_axia_safe_nav2_navigation", "__file__": str(path)}
        exec(drop_docking_from_navigation_source(source), namespace)
    else:
        namespace = runpy.run_path(str(path))
    return namespace["generate_launch_description"]()


def replace_upstream_include(description, original_basename: str, safe_launch: Path):
    # Use public LaunchDescription/Include/GroupAction interfaces only.
    from launch.actions import GroupAction, IncludeLaunchDescription
    from launch.launch_description_sources import PythonLaunchDescriptionSource

    if Path(safe_launch).name not in {"axia_bringup_p0.launch.py",
                                     "axia_navigation_p0.launch.py",
                                     "axia_bringup_p1.launch.py",
                                     "axia_navigation_p1.launch.py"}:
        raise ValueError("Unapproved replacement launch path")

    collections = [description.entities]
    for action in description.entities:
        if isinstance(action, GroupAction):
            collections.append(action.get_sub_entities())

    matches = []
    for collection in collections:
        for idx, action in enumerate(collection):
            if not isinstance(action, IncludeLaunchDescription):
                continue
            # Jazzy LaunchDescriptionSource.location is often a stringified
            # TextSubstitution object address until a LaunchContext is present.
            # Instead match the official include's EXACT public argument signature.
            arguments = tuple(name for name, _ in action.launch_arguments)
            expected = {
                "navigation_launch.py": {
                    "namespace", "use_sim_time", "autostart", "params_file",
                    "use_composition", "use_respawn", "container_name"
                },
                "bringup_launch.py": {
                    "namespace", "use_namespace", "slam", "map", "use_sim_time",
                    "params_file", "autostart", "use_composition", "use_respawn"
                },
            }
            if set(arguments) == expected.get(original_basename, set()):
                matches.append((collection, idx, action))

    if len(matches) != 1:
        diagnostic = []
        for collection in collections:
            for element in collection:
                diagnostic.append((
                    type(element).__name__,
                    getattr(getattr(element, "launch_description_source", None), "location", None),
                ))
        raise ValueError(
            f"Expected exactly one official {original_basename} include; got {len(matches)}; "
            f"observed={diagnostic}"
        )
    collection, idx, original = matches[0]
    collection[idx] = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(str(safe_launch)),
        launch_arguments=original.launch_arguments,
        condition=original.condition,
    )
    return description
