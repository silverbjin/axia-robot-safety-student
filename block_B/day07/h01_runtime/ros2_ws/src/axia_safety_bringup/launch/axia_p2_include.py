"""Fail-closed exact launch Include replacement for P2, leaving P1 untouched."""
from pathlib import Path
from launch.actions import GroupAction, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource

SIGS = {
    'bringup_launch.py': {'namespace','use_namespace','slam','map','use_sim_time',
                          'params_file','autostart','use_composition','use_respawn'},
    'navigation_launch.py': {'namespace','use_sim_time','autostart','params_file',
                              'use_composition','use_respawn','container_name'},
}
ALLOW = {'axia_bringup_p2.launch.py', 'axia_navigation_p2.launch.py'}


def replace_include(description, official_name, p2_path):
    if official_name not in SIGS or Path(p2_path).name not in ALLOW:
        raise ValueError('Unexpected P2 include target')
    matches = []
    collections = [description.entities]
    for action in description.entities:
        if isinstance(action, GroupAction):
            collections.append(action.get_sub_entities())
    for collection in collections:
        for i, action in enumerate(collection):
            if isinstance(action, IncludeLaunchDescription) and (
                {k for k, _ in action.launch_arguments} == SIGS[official_name]
            ):
                matches.append((collection, i, action))
    if len(matches) != 1:
        raise ValueError(f'Expected one official {official_name} include, got {len(matches)}')
    c, index, old = matches[0]
    c[index] = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(str(p2_path)),
        launch_arguments=old.launch_arguments, condition=old.condition)
    return description
