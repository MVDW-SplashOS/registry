import os
import sys
import argparse
import shutil
import subprocess
import yaml
import json
import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List

# Add parent directory to path to import libregistry
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "lib"))

# Get the project root directory
PROJECT_ROOT = Path(__file__).parent.parent.parent


try:
    from libregistry import (
        RegistrySession,
        decoder,
        encoder,
        File,
        get_main_definition,
        get_package_definition,
        RegistryError,
    )
except ImportError as e:
    print(f"Error: Could not import libregistry. Make sure it's installed: {e}")
    sys.exit(1)


class RegistryCLI:
    """Main CLI class for registry operations"""

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
        """Ensure required directories exist"""
        try:
            self.changes_file.parent.mkdir(parents=True, exist_ok=True)
            self.backup_dir.mkdir(parents=True, exist_ok=True)
        except PermissionError:
            # Fall back to user's home directory
            home_registry = Path.home() / ".registry"
            self.changes_file = home_registry / "changes.yaml"
            self.backup_dir = home_registry / "backups"
            self.changes_file.parent.mkdir(parents=True, exist_ok=True)
            self.backup_dir.mkdir(parents=True, exist_ok=True)

    def _load_changes(self) -> Dict[str, Any]:
        """Load pending changes from file"""
        if not self.changes_file.exists():
            return {}

        try:
            with open(self.changes_file, "r") as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            print(f"Warning: Could not load changes file: {e}")
            return {}

    def _save_changes(self, changes: Dict[str, Any]):
        """Save pending changes to file atomically"""
        import tempfile
        import os as _os

        try:
            changes_file_dir = self.changes_file.parent
            fd, tmp_path = tempfile.mkstemp(
                dir=changes_file_dir,
                prefix=".changes_",
                suffix=".tmp"
            )
            try:
                with _os.fdopen(fd, "w") as f:
                    yaml.dump(changes, f, default_flow_style=False)
                _os.replace(tmp_path, self.changes_file)
            except Exception:
                try:
                    _os.unlink(tmp_path)
                except OSError:
                    pass
                raise
        except Exception as e:
            print(f"Error: Could not save changes file: {e}")
            sys.exit(1)

    def _parse_path(self, path: str) -> tuple:
        """Parse registry path into components"""
        import re

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

        if not re.match(r'^[a-zA-Z0-9_\-\.]+$', category):
            raise ValueError(f"Invalid category name: {category}")
        if not re.match(r'^[a-zA-Z0-9_\-\.]+$', package):
            raise ValueError(f"Invalid package name: {package}")

        return category, package, config_path

    def _get_config_structure(
        self, category: str, package: str, config_path: str
    ) -> Dict[str, Any]:
        """Get configuration structure for a package"""
        main_def = get_main_definition()
        pkg_def = get_package_definition(main_def, category, package)

        if not pkg_def:
            raise ValueError(f"Package not found: {category}/{package}")

        # Find the configuration structure
        structures = pkg_def.get("structure", {})

        # Extract the base config name (e.g., "sshd_config" from "sshd_config/X11Forwarding")
        base_config_path = (
            config_path.split("/")[0] if "/" in config_path else config_path
        )

        for struct_name, struct_file in structures.items():
            if struct_name == base_config_path or struct_file == base_config_path:
                # Load the structure definition
                struct_path = (
                    Path("/etc/registry/definitions") / category / package / struct_file
                )
                if struct_path.exists():
                    with open(struct_path, "r") as f:
                        return yaml.safe_load(f)

        # Try to find the structure file directly
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

    def _get_config_file_path(self, structure: Dict[str, Any]) -> Path:
        """Get the actual configuration file path from structure"""
        file_info = structure.get("file", {})
        location = file_info.get("location")
        if not location:
            raise ValueError("No file location specified in structure")
        return Path(location)

    def set_command(self, path: str, value: str):
        """Set a configuration value"""
        try:
            category, package, config_path = self._parse_path(path)

            parsed_value = self._parse_value(value)

            try:
                self._get_config_structure(category, package, config_path)
            except Exception as e:
                if self.verbose:
                    raise
                print(f"Warning: Could not validate structure for {path}: {e}")

            changes = self._load_changes()

            if category not in changes:
                changes[category] = {}
            if package not in changes[category]:
                changes[category][package] = {}
            if config_path not in changes[category][package]:
                changes[category][package][config_path] = {}

            changes[category][package][config_path] = parsed_value

            self._save_changes(changes)

            print(f"Set {path} = {parsed_value}")

        except RegistryError as e:
            print(f"Registry error: {e}")
            if self.verbose:
                import traceback
                traceback.print_exc()
            sys.exit(1)
        except Exception as e:
            print(f"Error setting value: {e}")
            if self.verbose:
                import traceback
                traceback.print_exc()
            sys.exit(1)

    def _parse_value(self, value: str) -> Any:
        """Parse string value into appropriate type"""
        # Try boolean
        if value.lower() in ["true", "yes", "on", "1"]:
            return True
        elif value.lower() in ["false", "no", "off", "0"]:
            return False

        # Try integer
        try:
            return int(value)
        except ValueError:
            pass

        # Try float
        try:
            return float(value)
        except ValueError:
            pass

        # Return as string
        return value

    def apply_command(self):
        """Apply all pending changes"""
        changes = self._load_changes()

        if not changes:
            print("No changes to apply")
            return

        permission_issues = self._check_permissions(changes)

        if permission_issues:
            print(f"\n{len(permission_issues)} change(s) require elevated privileges:")
            for issue in permission_issues:
                print(f"  - {issue}")

            print("\nThese changes require elevated privileges.")
            print("Please run the following command to apply them:")
            registry_path = shutil.which("registry") or "registry"
            print(f"  sudo {registry_path} apply")
            print("\nOr press Ctrl+C to cancel.")
            return

        applied_count = 0
        failed_count = 0
        backups = []

        for category, packages in changes.items():
            for package, configs in packages.items():
                for config_path, value in configs.items():
                    try:
                        backup_info = self._apply_single_change(
                            category, package, config_path, value
                        )
                        if backup_info:
                            applied_count += 1
                            backups.append(backup_info)
                        else:
                            failed_count += 1
                    except Exception as e:
                        print(f"Error applying {category}/{package}/{config_path}: {e}")
                        if self.verbose:
                            import traceback
                            traceback.print_exc()
                        failed_count += 1

        if failed_count > 0:
            print(f"\nWarning: {failed_count} change(s) failed")
            if backups and input("Rollback changes? (y/n): ").lower() == 'y':
                self._rollback_changes(backups)
                print("Rollback complete")
                return

        if applied_count > 0:
            self._save_changes({})
            print(f"Applied {applied_count} change(s)")
        else:
            print("No changes were successfully applied")

    def _rollback_changes(self, backups: list):
        """Rollback applied changes from backups"""
        for backup_info in backups:
            config_file = backup_info["config_file"]
            backup_path = backup_info["backup_path"]
            try:
                if backup_path.exists():
                    shutil.copy2(backup_path, config_file)
                    if self.verbose:
                        print(f"Rolled back: {config_file}")
            except Exception as e:
                print(f"Failed to rollback {config_file}: {e}")

    def _check_permissions(self, changes: Dict[str, Any]) -> List[str]:
        """Check if we have write permissions for all configuration files"""
        permission_issues = []

        for category, packages in changes.items():
            for package, configs in packages.items():
                for config_path, value in configs.items():
                    try:
                        structure = self._get_config_structure(
                            category, package, config_path
                        )
                        config_file = self._get_config_file_path(structure)

                        # Check if we can write to the file
                        if config_file.exists():
                            if not os.access(config_file, os.W_OK):
                                permission_issues.append(
                                    f"{category}/{package}/{config_path}"
                                )
                        else:
                            # Check if we can write to the directory
                            if not os.access(config_file.parent, os.W_OK):
                                permission_issues.append(
                                    f"{category}/{package}/{config_path}"
                                )
                    except Exception:
                        # If we can't even read the structure, assume permission issue
                        permission_issues.append(f"{category}/{package}/{config_path}")

        return permission_issues

    def _apply_single_change(
        self, category: str, package: str, config_path: str, value: Any
    ) -> dict:
        """Apply a single configuration change"""
        backup_info = None
        try:
            structure = self._get_config_structure(category, package, config_path)
            config_file = self._get_config_file_path(structure)

            if config_file.exists() and os.access(config_file.parent, os.W_OK):
                backup_path = self.backup_dir / f"{config_file.name}.{os.getpid()}.bak"
                try:
                    shutil.copy2(config_file, backup_path)
                    backup_info = {
                        "config_file": config_file,
                        "backup_path": backup_path,
                    }
                except (PermissionError, OSError) as e:
                    if self.verbose:
                        print(f"Warning: Could not create backup for {config_file}: {e}")

            # Read current configuration
            if config_file.exists():
                current_config = decoder.decode_file(str(config_file), structure)
            else:
                current_config = {}

            # Apply the change
            # Parse the config_path to handle nested structures
            path_parts = config_path.split("/")
            if len(path_parts) == 1:
                # Simple case: config_path is just the option name
                if "main" not in current_config:
                    current_config["main"] = {}
                current_config["main"][path_parts[0]] = value
            else:
                # Complex case: config_path has structure (e.g., "sshd_config/X11Forwarding")
                # The first part is the structure name, the rest is the option path
                option_name = path_parts[-1]

                # Navigate to the correct section
                section = current_config
                for part in path_parts[:-1]:
                    if part not in section:
                        section[part] = {}
                    section = section[part]

                section[option_name] = value

            # Write back the configuration
            # Extract format from structure
            file_info = structure.get("file", {})
            format_type = file_info.get("format", "key-value")

            # Create encoding structure with format
            encoding_structure = {
                "format": format_type,
                "syntax": structure.get("syntax", {}),
            }

            encoded_content = encoder.encode_data(current_config, encoding_structure)
            file_obj = File(str(config_file))
            file_obj.write(encoded_content)

            print(f"Applied: {category}/{package}/{config_path} = {value}")
            return backup_info or {}

        except Exception as e:
            print(f"Failed to apply {category}/{package}/{config_path}: {e}")
            if self.verbose:
                import traceback
                traceback.print_exc()
            return {}

    def _apply_with_sudo(self):
        """Apply changes using sudo elevation"""
        print("\nAttempting to apply changes with elevated privileges...")

        # Get the path to this script
        script_path = Path(__file__).resolve()

        # Build sudo command
        cmd = ["sudo", sys.executable, str(script_path), "apply"]

        try:
            # Run with sudo
            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode == 0:
                print("✅ Changes applied successfully with elevated privileges")
                # Clear changes file
                self._save_changes({})
                return True
            else:
                print(f"❌ Failed to apply changes with sudo: {result.stderr}")
                return False

        except subprocess.CalledProcessError as e:
            print(f"❌ Sudo command failed: {e}")
            return False
        except Exception as e:
            print(f"❌ Unexpected error during sudo execution: {e}")
            return False

    def discard_command(self):
        """Discard all pending changes"""
        changes = self._load_changes()

        if not changes:
            print("No changes to discard")
            return

        change_count = sum(
            len(configs)
            for packages in changes.values()
            for configs in packages.values()
        )
        self._save_changes({})
        print(f"Discarded {change_count} pending change(s)")

    def reset_command(self, path: str):
        """Reset a specific configuration to its default or remove pending changes"""
        try:
            category, package, config_path = self._parse_path(path)

            changes = self._load_changes()

            # Remove the specific change
            if (
                category in changes
                and package in changes[category]
                and config_path in changes[category][package]
            ):
                del changes[category][package][config_path]

                # Clean up empty structures
                if not changes[category][package]:
                    del changes[category][package]
                if not changes[category]:
                    del changes[category]

                self._save_changes(changes)
                print(f"Reset {path}")
            else:
                print(f"No pending changes for {path}")

        except Exception as e:
            print(f"Error resetting configuration: {e}")
            sys.exit(1)

    def view_changes_command(self):
        """View all pending changes"""
        changes = self._load_changes()

        if not changes:
            print("No pending changes")
            return

        print("Pending changes:")
        print("-" * 50)

        for category, packages in changes.items():
            print(f"{category}:")
            for package, configs in packages.items():
                print(f"  {package}:")
                for config_path, value in configs.items():
                    print(f"    {config_path} = {value}")

        print("-" * 50)
        total_changes = sum(
            len(configs)
            for packages in changes.values()
            for configs in packages.values()
        )
        print(f"Total: {total_changes} change(s) pending")

    def get_command(self, path: str):
        """Get a configuration value"""
        try:
            category, package, config_path = self._parse_path(path)

            structure = self._get_config_structure(category, package, config_path)
            config_file = self._get_config_file_path(structure)

            if not config_file.exists():
                print(f"Configuration file does not exist: {config_file}")
                return

            current_config = decoder.decode_file(str(config_file), structure)

            path_parts = config_path.split("/")
            value = current_config
            for part in path_parts:
                if isinstance(value, dict) and part in value:
                    value = value[part]
                else:
                    print(f"Option not found: {path}")
                    return

            print(f"{path} = {value}")

        except Exception as e:
            print(f"Error getting value: {e}")
            sys.exit(1)

    def diff_command(self):
        """Show diff between current config and pending changes"""
        changes = self._load_changes()

        if not changes:
            print("No pending changes to show")
            return

        print("Pending changes (diff):")
        print("=" * 60)

        for category, packages in changes.items():
            for package, configs in packages.items():
                for config_path, new_value in configs.items():
                    try:
                        structure = self._get_config_structure(category, package, config_path)
                        config_file = self._get_config_file_path(structure)

                        print(f"\n{category}/{package}/{config_path}:")
                        print(f"  Config file: {config_file}")

                        if config_file.exists():
                            current_config = decoder.decode_file(str(config_file), structure)

                            path_parts = config_path.split("/")
                            old_value = current_config
                            for part in path_parts:
                                if isinstance(old_value, dict) and part in old_value:
                                    old_value = old_value[part]
                                else:
                                    old_value = "<not set>"
                                    break

                            print(f"  Current value: {old_value}")
                            print(f"  New value:     {new_value}")
                        else:
                            print("  Current value: <file does not exist>")
                            print(f"  New value:     {new_value}")

                    except Exception as e:
                        print(f"  Error: {e}")

        print("\n" + "=" * 60)

    def validate_command(self):
        """Validate pending changes against their definitions"""
        changes = self._load_changes()

        if not changes:
            print("No pending changes to validate")
            return

        errors = []
        valid_count = 0

        for category, packages in changes.items():
            for package, configs in packages.items():
                for config_path, value in configs.items():
                    try:
                        structure = self._get_config_structure(category, package, config_path)
                        config_file = self._get_config_file_path(structure)

                        format_type = structure.get("file", {}).get("format", "key-value")
                        encoding_structure = {
                            "format": format_type,
                            "syntax": structure.get("syntax", {}),
                            "structures": structure.get("structures", {}),
                        }

                        current_config = {}
                        if config_file.exists():
                            current_config = decoder.decode_file(str(config_file), structure)

                        path_parts = config_path.split("/")
                        if len(path_parts) == 1:
                            if "main" not in current_config:
                                current_config["main"] = {}
                            current_config["main"][path_parts[0]] = value
                        else:
                            option_name = path_parts[-1]
                            section = current_config
                            for part in path_parts[:-1]:
                                if part not in section:
                                    section[part] = {}
                                section = section[part]
                            section[option_name] = value

                        filetype_decoder = decoder.get_filetype_decoder(format_type)
                        if filetype_decoder:
                            validation_errors = filetype_decoder.validate(
                                current_config, encoding_structure
                            )
                            if validation_errors:
                                errors.append(
                                    f"{category}/{package}/{config_path}: "
                                    + "; ".join(validation_errors)
                                )
                            else:
                                valid_count += 1
                        else:
                            valid_count += 1

                    except Exception as e:
                        errors.append(f"{category}/{package}/{config_path}: {e}")

        if errors:
            print("Validation errors found:")
            for error in errors:
                print(f"  - {error}")
            sys.exit(1)
        else:
            print(f"All {valid_count} change(s) validated successfully")

    def list_command(self, category: str = None, detected_only: bool = False):
        """List available packages"""
        try:
            definitions_dir = Path("/etc/registry/definitions")

            if not definitions_dir.exists():
                definitions_dir = PROJECT_ROOT / "definitions"

            categories = []
            packages = {}

            if definitions_dir.exists():
                for cat_dir in sorted(definitions_dir.iterdir()):
                    if cat_dir.is_dir() and not cat_dir.name.startswith("."):
                        if category and cat_dir.name != category:
                            continue

                        cat_packages = []
                        for pkg_dir in sorted(cat_dir.iterdir()):
                            if pkg_dir.is_dir() and (pkg_dir / "manifest.yaml").exists():
                                manifest_path = pkg_dir / "manifest.yaml"
                                with open(manifest_path) as f:
                                    manifest = yaml.safe_load(f)

                                pkg_info = {
                                    "name": pkg_dir.name,
                                    "version": manifest.get("application", {}).get("version", "unknown"),
                                    "detected": False,
                                }

                                if not detected_only:
                                    cat_packages.append(pkg_info)
                                else:
                                    detect_paths = manifest.get("detect_installed", [])
                                    is_installed = any(Path(p).exists() for p in detect_paths)
                                    if is_installed:
                                        pkg_info["detected"] = True
                                        cat_packages.append(pkg_info)

                        if cat_packages:
                            categories.append(cat_dir.name)
                            packages[cat_dir.name] = cat_packages

            if category:
                print(f"Packages in '{category}':")
                if category in packages:
                    for pkg in packages[category]:
                        status = " [installed]" if detected_only and pkg["detected"] else ""
                        print(f"  - {pkg['name']} (v{pkg['version']}){status}")
                else:
                    print("  No packages found")
            else:
                print("Available packages:")
                print("=" * 50)
                for cat in categories:
                    print(f"\n{cat}:")
                    for pkg in packages[cat]:
                        status = " [installed]" if pkg["detected"] else ""
                        print(f"  - {pkg['name']} (v{pkg['version']}){status}")
                print("\n" + "=" * 50)

        except Exception as e:
            print(f"Error listing packages: {e}")
            if self.verbose:
                import traceback
                traceback.print_exc()
            sys.exit(1)

    def search_command(self, query: str):
        """Search for packages"""
        try:
            definitions_dir = Path("/etc/registry/definitions")

            if not definitions_dir.exists():
                definitions_dir = PROJECT_ROOT / "definitions"

            results = []

            if definitions_dir.exists():
                for cat_dir in definitions_dir.iterdir():
                    if cat_dir.is_dir() and not cat_dir.name.startswith("."):
                        for pkg_dir in cat_dir.iterdir():
                            if pkg_dir.is_dir() and (pkg_dir / "manifest.yaml").exists():
                                manifest_path = pkg_dir / "manifest.yaml"
                                with open(manifest_path) as f:
                                    manifest = yaml.safe_load(f)

                                pkg_name = pkg_dir.name
                                app_name = manifest.get("application", {}).get("name", "").lower()
                                query_lower = query.lower()

                                if query_lower in pkg_name or query_lower in app_name:
                                    results.append({
                                        "category": cat_dir.name,
                                        "name": pkg_name,
                                        "version": manifest.get("application", {}).get("version", "unknown"),
                                    })

            if results:
                print(f"Search results for '{query}':")
                print("=" * 50)
                for result in results:
                    print(f"  {result['category']}/{result['name']} (v{result['version']})")
                print("=" * 50)
            else:
                print(f"No results found for '{query}'")

        except Exception as e:
            print(f"Error searching: {e}")
            sys.exit(1)

    def info_command(self, package: str):
        """Show package information"""
        try:
            parts = package.split("/")
            if len(parts) != 2:
                print("Invalid package format. Use: category/package")
                sys.exit(1)

            category, pkg_name = parts

            definitions_dir = Path("/etc/registry/definitions")
            if not definitions_dir.exists():
                definitions_dir = PROJECT_ROOT / "definitions"

            pkg_dir = definitions_dir / category / pkg_name
            if not pkg_dir.exists():
                print(f"Package not found: {category}/{pkg_name}")
                sys.exit(1)

            manifest_path = pkg_dir / "manifest.yaml"
            if not manifest_path.exists():
                print(f"No manifest found for {category}/{pkg_name}")
                sys.exit(1)

            with open(manifest_path) as f:
                manifest = yaml.safe_load(f)

            print(f"Package: {pkg_name}")
            print("=" * 50)
            print(f"Category: {category}")
            print(f"Version: {manifest.get('application', {}).get('version', 'unknown')}")
            print(f"Definition version: {manifest.get('definition', {}).get('libregistry_minimum_version', 'unknown')}")

            structures = manifest.get("structure", {})
            if structures:
                print("\nConfiguration files:")
                for struct_name, struct_file in structures.items():
                    struct_path = pkg_dir / f"{struct_file}.yaml"
                    if not struct_path.exists():
                        struct_path = pkg_dir / struct_file

                    if struct_path.exists():
                        with open(struct_path) as f:
                            struct_def = yaml.safe_load(f)

                        file_info = struct_def.get("file", {})
                        location = file_info.get("location", "unknown")
                        format_type = file_info.get("format", "unknown")
                        print(f"  - {struct_name}: {location} (format: {format_type})")

            detect_paths = manifest.get("detect_installed", [])
            if detect_paths:
                print("\nDetection paths:")
                for path in detect_paths:
                    exists = Path(path).exists()
                    status = "[installed]" if exists else "[not found]"
                    print(f"  - {path} {status}")

        except Exception as e:
            print(f"Error getting info: {e}")
            sys.exit(1)

    def detect_command(self, package: str = None):
        """Detect installed packages"""
        self.list_command(category=package, detected_only=True)

    def validate_config_command(self, path: str, strict: bool = False):
        """Validate a configuration file against its definition"""
        try:
            parts = path.split("/")
            if len(parts) < 3:
                print("Invalid path format. Use: category/package/config_path")
                sys.exit(1)

            category = parts[0]
            package = parts[1]
            config_path = "/".join(parts[2:])

            structure = self._get_config_structure(category, package, config_path)
            config_file = self._get_config_file_path(structure)

            if not config_file.exists():
                print(f"Configuration file does not exist: {config_file}")
                sys.exit(1)

            print(f"Validating: {config_file}")
            print("=" * 60)

            current_config = decoder.decode_file(str(config_file), structure)

            format_type = structure.get("file", {}).get("format", "key-value")
            encoding_structure = {
                "format": format_type,
                "syntax": structure.get("syntax", {}),
                "structures": structure.get("structures", {}),
            }

            filetype_decoder = decoder.get_filetype_decoder(format_type)
            if filetype_decoder:
                validation_errors = filetype_decoder.validate(current_config, encoding_structure)
                if validation_errors:
                    print(f"Validation FAILED ({len(validation_errors)} error(s)):")
                    for error in validation_errors:
                        print(f"  - {error}")
                    sys.exit(1)
                else:
                    print("Validation PASSED")
            else:
                print(f"No validator available for format: {format_type}")

        except Exception as e:
            print(f"Error validating config: {e}")
            if self.verbose:
                import traceback
                traceback.print_exc()
            sys.exit(1)

    def export_command(self, file_path: str = None, format: str = "yaml"):
        """Export registry state"""
        try:
            changes = self._load_changes()
            backups = []

            if self.backup_dir.exists():
                for backup in self.backup_dir.glob("*.bak"):
                    backups.append({
                        "name": backup.name,
                        "path": str(backup),
                        "timestamp": backup.stat().st_mtime,
                    })

            export_data = {
                "version": "1.0",
                "changes": changes,
                "backups": backups,
                "metadata": {
                    "exported_at": str(datetime.datetime.now()),
                    "version": "0.1.0",
                }
            }

            if format == "json":
                output = json.dumps(export_data, indent=2)
            else:
                output = yaml.dump(export_data, default_flow_style=False)

            if file_path:
                with open(file_path, "w") as f:
                    f.write(output)
                print(f"Exported to: {file_path}")
            else:
                print(output)

        except Exception as e:
            print(f"Error exporting: {e}")
            if self.verbose:
                import traceback
                traceback.print_exc()
            sys.exit(1)

    def import_command(self, file_path: str, merge: bool = False):
        """Import registry state"""
        try:
            with open(file_path, "r") as f:
                if file_path.endswith(".json"):
                    import_data = json.load(f)
                else:
                    import_data = yaml.safe_load(f)

            if "version" not in import_data:
                print("Invalid import file: missing version")
                sys.exit(1)

            imported_changes = import_data.get("changes", {})

            if not merge:
                current_changes = {}
            else:
                current_changes = self._load_changes()
                for cat, packages in imported_changes.items():
                    if cat not in current_changes:
                        current_changes[cat] = {}
                    for pkg, configs in packages.items():
                        if pkg not in current_changes[cat]:
                            current_changes[cat][pkg] = {}
                        current_changes[cat][pkg].update(configs)

            self._save_changes(current_changes)
            print(f"Imported {len(imported_changes)} change(s)")

        except Exception as e:
            print(f"Error importing: {e}")
            if self.verbose:
                import traceback
                traceback.print_exc()
            sys.exit(1)

    def backup_list_command(self):
        """List available backups"""
        if not self.backup_dir.exists():
            print("No backups found")
            return

        backups = sorted(self.backup_dir.glob("*.bak"), key=lambda p: p.stat().st_mtime, reverse=True)

        if not backups:
            print("No backups found")
            return

        print("Available backups:")
        print("=" * 60)
        for backup in backups:
            mtime = backup.stat().st_mtime
            timestamp = datetime.datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
            print(f"  {backup.name}")
            print(f"    Created: {timestamp}")
            print(f"    Path: {backup}")
            print()
        print("=" * 60)

    def _find_original_path(self, backup_name: str) -> Optional[Path]:
        """Try to find the original path for a backup file from definitions."""
        original_name = Path(backup_name).stem

        definitions_dir = Path("/etc/registry/definitions")
        if not definitions_dir.exists():
            definitions_dir = PROJECT_ROOT / "definitions"

        if definitions_dir.exists():
            for cat_dir in definitions_dir.iterdir():
                if cat_dir.is_dir():
                    for pkg_dir in cat_dir.iterdir():
                        if pkg_dir.is_dir():
                            manifest_path = pkg_dir / "manifest.yaml"
                            if manifest_path.exists():
                                try:
                                    with open(manifest_path) as f:
                                        manifest = yaml.safe_load(f)
                                    structures = manifest.get("structure", {})
                                    for struct_name, struct_file in structures.items():
                                        if struct_name == original_name or struct_file == original_name:
                                            struct_path = pkg_dir / f"{struct_file}.yaml"
                                            if not struct_path.exists():
                                                struct_path = pkg_dir / struct_file
                                            if struct_path.exists():
                                                with open(struct_path) as f:
                                                    struct_def = yaml.safe_load(f)
                                                file_info = struct_def.get("file", {})
                                                location = file_info.get("location")
                                                if location:
                                                    return Path(location)
                                except Exception:
                                    continue
        return None

    def backup_restore_command(self, backup_name: str):
        """Restore from a backup"""
        if not self.backup_dir.exists():
            print("No backups found")
            sys.exit(1)

        backup_path = self.backup_dir / backup_name
        if not backup_path.exists():
            backup_path = self.backup_dir / f"{backup_name}.bak"
            if not backup_path.exists():
                print(f"Backup not found: {backup_name}")
                sys.exit(1)

        original_path = self._find_original_path(backup_path.name)

        if not original_path:
            print(f"Could not determine original location for: {backup_path.stem}")
            print(f"Backup file: {backup_path}")
            user_input = input("Enter original file path (or press Enter to cancel): ").strip()
            if user_input:
                original_path = Path(user_input)
            else:
                sys.exit(1)

        if not original_path.parent.exists():
            print(f"Directory does not exist: {original_path.parent}")
            sys.exit(1)

        try:
            shutil.copy2(backup_path, original_path)
            print(f"Restored: {original_path}")
            print(f"From backup: {backup_path}")
        except Exception as e:
            print(f"Error restoring backup: {e}")
            if self.verbose:
                import traceback
                traceback.print_exc()
            sys.exit(1)

    def backup_delete_command(self, backup_name: str):
        """Delete a backup"""
        backup_path = self.backup_dir / backup_name
        if not backup_path.exists():
            backup_path = self.backup_dir / f"{backup_name}.bak"
            if not backup_path.exists():
                print(f"Backup not found: {backup_name}")
                sys.exit(1)

        try:
            backup_path.unlink()
            print(f"Deleted backup: {backup_name}")
        except Exception as e:
            print(f"Error deleting backup: {e}")
            sys.exit(1)


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Registry - System configuration management tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  registry set system_applications/openssh-server/sshd_config/Port 2222
  registry get system_applications/openssh-server/sshd_config/Port
  registry validate-config system_applications/openssh-server/sshd_config
  registry diff
  registry validate
  registry apply
  registry discard
  registry reset system_applications/openssh-server/sshd_config/Port
  registry view changes
  registry list
  registry search openssh
  registry info system_applications/openssh-server
  registry detect
  registry export --file backup.yaml
  registry import backup.yaml
        """,
    )

    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose output"
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # set command
    set_parser = subparsers.add_parser("set", help="Set a configuration value")
    set_parser.add_argument(
        "path", help="Configuration path (category/package/config/option)"
    )
    set_parser.add_argument("value", help="Value to set")

    # apply command
    subparsers.add_parser("apply", help="Apply all pending changes")

    # discard command
    subparsers.add_parser("discard", help="Discard all pending changes")

    # reset command
    reset_parser = subparsers.add_parser("reset", help="Reset a configuration")
    reset_parser.add_argument("path", help="Configuration path to reset")

    # view changes command
    subparsers.add_parser("view-changes", help="View pending changes")

    # get command
    get_parser = subparsers.add_parser("get", help="Get a configuration value")
    get_parser.add_argument("path", help="Configuration path (category/package/config/option)")

    # diff command
    subparsers.add_parser("diff", help="Show diff of pending changes")

    # validate command
    subparsers.add_parser("validate", help="Validate pending changes against definitions")

    # validate-config command
    validate_config_parser = subparsers.add_parser("validate-config", help="Validate a config file")
    validate_config_parser.add_argument("path", help="Configuration path (category/package/config)")
    validate_config_parser.add_argument("--strict", action="store_true", help="Enable strict validation")

    # list command
    list_parser = subparsers.add_parser("list", help="List available packages")
    list_parser.add_argument("category", nargs="?", help="Category to list (optional)")
    list_parser.add_argument("--detected", "-d", action="store_true", help="Show only detected packages")

    # search command
    search_parser = subparsers.add_parser("search", help="Search for packages")
    search_parser.add_argument("query", help="Search query")

    # info command
    info_parser = subparsers.add_parser("info", help="Show package information")
    info_parser.add_argument("package", help="Package (category/name)")

    # detect command
    detect_parser = subparsers.add_parser("detect", help="Detect installed packages")
    detect_parser.add_argument("package", nargs="?", help="Package to check (optional)")

    # backup subcommand
    backup_subparsers = subparsers.add_parser("backup", help="Backup operations")
    backup_subparsers.add_argument("action", choices=["list", "restore", "delete"], help="Backup action")
    backup_subparsers.add_argument("backup_name", nargs="?", help="Backup name (for restore/delete)")

    # export command
    export_parser = subparsers.add_parser("export", help="Export registry state")
    export_parser.add_argument("--file", "-f", help="Output file path")
    export_parser.add_argument("--format", choices=["yaml", "json"], default="yaml", help="Export format")

    # import command
    import_parser = subparsers.add_parser("import", help="Import registry state")
    import_parser.add_argument("file", help="Import file path")
    import_parser.add_argument("--merge", "-m", action="store_true", help="Merge with existing changes")

    args = parser.parse_args()

    cli = RegistryCLI(verbose=args.verbose)

    if args.command == "set":
        cli.set_command(args.path, args.value)
    elif args.command == "apply":
        cli.apply_command()
    elif args.command == "discard":
        cli.discard_command()
    elif args.command == "reset":
        cli.reset_command(args.path)
    elif args.command == "view-changes":
        cli.view_changes_command()
    elif args.command == "get":
        cli.get_command(args.path)
    elif args.command == "diff":
        cli.diff_command()
    elif args.command == "validate":
        cli.validate_command()
    elif args.command == "validate-config":
        cli.validate_config_command(args.path, strict=args.strict)
    elif args.command == "list":
        cli.list_command(category=args.category, detected_only=args.detected)
    elif args.command == "search":
        cli.search_command(args.query)
    elif args.command == "info":
        cli.info_command(args.package)
    elif args.command == "detect":
        cli.detect_command(args.package)
    elif args.command == "backup":
        if args.action == "list":
            cli.backup_list_command()
        elif args.action == "restore" and args.backup_name:
            cli.backup_restore_command(args.backup_name)
        elif args.action == "delete" and args.backup_name:
            cli.backup_delete_command(args.backup_name)
        else:
            print("Usage: registry backup list")
            sys.exit(1)
    elif args.command == "export":
        cli.export_command(file_path=args.file, format=args.format)
    elif args.command == "import":
        cli.import_command(args.file, merge=args.merge)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
