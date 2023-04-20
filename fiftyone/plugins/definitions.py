"""
FiftyOne Server ``/plugins`` route.

| Copyright 2017-2023, Voxel51, Inc.
| `voxel51.com <https://voxel51.com/>`_
|
"""
import glob
import os
import eta.core.serial as etas
import fiftyone as fo
import os
import yaml  # BEFORE PR: add to requirements.txt
import importlib
import sys
import traceback
from enum import Enum

# BEFORE PR: where should this go?
def find_files(root_dir, filename, extensions, max_depth):
    """Returns all files matching the given pattern, up to the given depth.

    Args:
        pattern: a glob pattern
        max_depth: the maximum depth to search

    Returns:
        a list of paths
    """
    if max_depth == 0:
        return []

    paths = []
    for i in range(1, max_depth):
        pattern_parts = [root_dir]
        pattern_parts += list("*" * i)
        pattern_parts += [filename]
        pattern = os.path.join(*pattern_parts)
        for extension in extensions:
            paths += glob.glob(pattern + "." + extension)

    return paths


MAX_PLUGIN_SEARCH_DEPTH = 3
PLUGIN_METADATA_FILENAME = "fiftyone"
PLUGIN_METADATA_EXTENSIONS = ["yml", "yaml"]


def find_plugin_metadata_files():
    plugins_dir = fo.config.plugins_dir

    if not plugins_dir:
        return []

    normal_locations = find_files(
        plugins_dir,
        PLUGIN_METADATA_FILENAME,
        PLUGIN_METADATA_EXTENSIONS,
        MAX_PLUGIN_SEARCH_DEPTH,
    )
    node_modules_locations = find_files(
        os.path.join(plugins_dir, "node_modules", "*"),
        PLUGIN_METADATA_FILENAME,
        PLUGIN_METADATA_EXTENSIONS,
        1,
    )
    yarn_packages_locations = find_files(
        os.path.join(plugins_dir, "packages", "*"),
        PLUGIN_METADATA_FILENAME,
        PLUGIN_METADATA_EXTENSIONS,
        1,
    )
    return normal_locations + node_modules_locations + yarn_packages_locations


class PluginTypes(Enum):
    JAVASCRIPT = "javascript"
    PYTHON = "python"


class PluginDefinition:
    def __init__(self, module_dir, metadata):
        self.module_dir = module_dir
        self.metadata = metadata
        self.name = metadata.get("name", None)
        self.version = metadata.get("version", None)
        self.license = metadata.get("license", None)
        self.description = metadata.get("description", None)
        self.fiftyone_compatibility = metadata.get("fiftyone", {}).get(
            "version", "*"
        )
        self.operators = metadata.get("operators", [])
        self.js_bundle = metadata.get("js_bundle", None)

    @property
    def type(self):
        return PluginTypes.JAVASCRIPT if self.js_bundle else PluginTypes.PYTHON


def load_plugin_definition(metadata_file):
    """Loads the plugin definition from the given metadata_file."""
    with open(metadata_file, "r") as f:
        metadata_dict = yaml.load(f, Loader=yaml.FullLoader)
        module_dir = os.path.basename(os.path.dirname(metadata_file))
        definition = PluginDefinition(module_dir, metadata_dict)
        if not definition.js_bundle:
            # check if package.json exists
            package_json_path = os.path.join(module_dir, "package.json")
            if os.path.exists(package_json_path):
                pkg = etas.read_json(package_json_path)
                definition.js_bundle = pkg.get("fiftyone", {}).get(
                    "script", None
                )


def list_plugins():
    """
    List all PluginDefinitions in the plugins directory.
    """
    plugins_dir = fo.config.plugins_dir

    if not plugins_dir:
        return []

    metadata_files = find_plugin_metadata_files()
    plugins = []
    for metadata_file in metadata_files:
        try:
            plugins.append(load_plugin_definition(metadata_file))
        except Exception as e:
            print("Error loading plugin metadata file: %s" % metadata_file)
            print(e)
            traceback.print_exc()
    return plugins