import os
import sys
import tempfile
import yaml
import re
from pathlib import Path
from typing import Dict, Any

from libregistry import (
    RegistrySession,
    get_main_definition,
    get_package_definition,
)

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent


class RegistryCore:
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.session = RegistrySession()
        etc_registry = Path("/etc/registry")
        if etc_registry.exists() and os.access(etc_registry, os.W_OK):
            self.changes_file = etc_registry / "changes.yaml"
            self.backup_dir = etc_registry / "backups"
        else:
            home_registry = Path.home() / ".registry"
            self.changes_file = home_registry / "changes.yaml"
            self.backup_dir = home_registry / "backups"
        self._ensure_directories()

    def _ensure_directories(self):
        try:
            self.changes_file.parent.mkdir(parents=True, exist_ok=True)
            self.backup_dir.mkdir(parents=True, exist_ok=True)
        except PermissionError:
            home_registry = Path.home() / ".registry"
            self.changes_file = home_registry / "changes.yaml"
            self.backup_dir = home_registry / "backups"
            self.changes_file.parent.mkdir(parents=True, exist_ok=True)
            self.backup_dir.mkdir(parents=True, exist_ok=True)

    def load_changes(self) -> Dict[str, Any]:
        if not self.changes_file.exists():
            return {}
        try:
            with open(self.changes_file, "r") as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            print(f"Warning: Could not load changes file: {e}")
            return {}

    def save_changes(self, changes: Dict[str, Any]):
        try:
            changes_file_dir = self.changes_file.parent
            fd, tmp_path = tempfile.mkstemp(
                dir=changes_file_dir, prefix=".changes_", suffix=".tmp"
            )
            try:
                with os.fdopen(fd, "w") as f:
                    yaml.dump(changes, f, default_flow_style=False)
                os.replace(tmp_path, self.changes_file)
            except Exception:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
                raise
        except Exception as e:
            print(f"Error: Could not save changes file: {e}")
            sys.exit(1)

    def parse_path(self, path: str) -> tuple:
        if not path or ".." in path or path.startswith("/"):
            raise ValueError(
                f"Invalid path format: {path}. Path must not be empty, absolute, or contain '..'"
            )
        parts = path.split("/")
        if len(parts) < 3:
            raise ValueError(
                f"Invalid path format: {path}. Expected: category/package/config_path"
            )
        category = parts[0]
        package = parts[1]
        config_path = "/".join(parts[2:])
        if not re.match(r"^[a-zA-Z0-9_\-\.]+$", category):
            raise ValueError(f"Invalid category name: {category}")
        if not re.match(r"^[a-zA-Z0-9_\-\.]+$", package):
            raise ValueError(f"Invalid package name: {package}")
        return category, package, config_path

    def get_config_structure(
        self, category: str, package: str, config_path: str
    ) -> Dict[str, Any]:
        main_def = get_main_definition()
        pkg_def = get_package_definition(main_def, category, package)
        if not pkg_def:
            raise ValueError(f"Package not found: {category}/{package}")
        structures = pkg_def.get("structure", {})
        base_config_path = (
            config_path.split("/")[0] if "/" in config_path else config_path
        )
        for struct_name, struct_file in structures.items():
            if struct_name == base_config_path or struct_file == base_config_path:
                struct_path = (
                    Path("/etc/registry/definitions") / category / package / struct_file
                )
                if struct_path.exists():
                    with open(struct_path, "r") as f:
                        return yaml.safe_load(f)
        struct_path = (
            Path("/etc/registry/definitions")
            / category
            / package
            / f"{base_config_path}.yaml"
        )
        if struct_path.exists():
            with open(struct_path, "r") as f:
                return yaml.safe_load(f)
        raise ValueError(f"Configuration structure not found: {config_path}")

    def get_config_file_path(self, structure: Dict[str, Any]) -> Path:
        file_info = structure.get("file", {})
        location = file_info.get("location")
        if not location:
            raise ValueError("No file location specified in structure")
        return Path(location)

    def parse_value(self, value: str) -> Any:
        if value.lower() in ["true", "yes", "on", "1"]:
            return True
        elif value.lower() in ["false", "no", "off", "0"]:
            return False
        try:
            return int(value)
        except ValueError:
            pass
        try:
            return float(value)
        except ValueError:
            pass
        return value

    def get_definitions_dir(self) -> Path:
        definitions_dir = Path("/etc/registry/definitions")
        if definitions_dir.exists():
            return definitions_dir
        return PROJECT_ROOT / "definitions"

    def check_permissions(self, changes: Dict[str, Any]) -> list:
        permission_issues = []
        for category, packages in changes.items():
            for package, configs in packages.items():
                for config_path, value in configs.items():
                    try:
                        structure = self.get_config_structure(
                            category, package, config_path
                        )
                        config_file = self.get_config_file_path(structure)
                        if config_file.exists():
                            if not os.access(config_file, os.W_OK):
                                permission_issues.append(
                                    f"{category}/{package}/{config_path}"
                                )
                        else:
                            if not os.access(config_file.parent, os.W_OK):
                                permission_issues.append(
                                    f"{category}/{package}/{config_path}"
                                )
                    except Exception:
                        permission_issues.append(f"{category}/{package}/{config_path}")
        return permission_issues
