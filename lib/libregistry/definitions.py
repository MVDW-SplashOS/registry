from . import const
from . import logger

import yaml
import os


def get_yaml(path):
    try:
        yaml_path = os.path.join(const.DIRECTORY_DEFINITION, path)
        with open(yaml_path, "r") as file:
            yaml_data = yaml.safe_load(file)
        return yaml_data
    except FileNotFoundError as e:
        logger.print_error(f"Definition YAML file not found: {path}")
    except Exception as e:
        logger.print_error(f"Failed to load definition YAML file: {path}", e)
    return {}


def get_main_definition():
    definition_manifest = get_yaml("manifest.yaml")
    definition_manifest["packages"] = {}

    for category in definition_manifest["categories"]:
        definition_manifest["packages"][category] = {}
        package_data = get_yaml(os.path.join(category, "packages.yaml"))
        definition_manifest["packages"][category] = package_data["packages"]

    return definition_manifest


def get_package_definition(main_definition, category, package, metadata_only=False):
    package_manifest = get_yaml(os.path.join(category, package, "manifest.yaml"))
    if len(package_manifest) == 0:
        logger.print_error(f"Package manifest is empty: {category}/{package}")
        return None
    return package_manifest
