from . import const
from .logger import get_logger

import yaml
import os

logger = get_logger("definitions")


def get_yaml(path):
    try:
        yaml_path = os.path.join(const.DIRECTORY_DEFINITION, path)
        with open(yaml_path, "r") as file:
            yaml_data = yaml.safe_load(file)
        return yaml_data
    except FileNotFoundError:
        logger.error("Definition YAML file not found: %s", path)
    except Exception:
        logger.error("Failed to load definition YAML file: %s", path)
    return {}


def get_main_definition():
    definition_manifest = get_yaml("manifest.yaml")
    if not definition_manifest or "categories" not in definition_manifest:
        return {"categories": [], "packages": {}}

    definition_manifest["packages"] = {}

    for category in definition_manifest["categories"]:
        definition_manifest["packages"][category] = {}
        package_data = get_yaml(os.path.join(category, "packages.yaml"))
        if package_data and "packages" in package_data:
            definition_manifest["packages"][category] = package_data["packages"]

    return definition_manifest


def get_package_definition(main_definition, category, package, metadata_only=False):
    package_manifest = get_yaml(os.path.join(category, package, "manifest.yaml"))
    if len(package_manifest) == 0:
        logger.error("Package manifest is empty: %s/%s", category, package)
        return None
    return package_manifest
