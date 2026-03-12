import os
import sys
import argparse
import tempfile
import shutil
import subprocess
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
        transformer,
        File,
        get_main_definition,
        get_package_definition,
        RegistryError,
        ConfigurationNotFoundError,
        PermissionDeniedError,
        ValidationError,
        EncodingError,
        DecodingError,
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
            import yaml

            with open(self.changes_file, "r") as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            print(f"Warning: Could not load changes file: {e}")
            return {}

    def _save_changes(self, changes: Dict[str, Any]):
        """Save pending changes to file"""
        try:
            import yaml

            with open(self.changes_file, "w") as f:
                yaml.dump(changes, f, default_flow_style=False)
        except Exception as e:
            print(f"Error: Could not save changes file: {e}")
            sys.exit(1)

    def _parse_path(self, path: str) -> tuple:
        """Parse registry path into components"""
        parts = path.split("/")
        if len(parts) < 3:
            raise ValueError(
                f"Invalid path format: {path}. Expected: category/package/config_path"
            )

        category = parts[0]
        package = parts[1]
        config_path = "/".join(parts[2:])

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
                    import yaml

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
            import yaml

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
                structure = self._get_config_structure(category, package, config_path)
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
                    except Exception as e:
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
                            print(f"  Current value: <file does not exist>")
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


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Registry - System configuration management tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  registry set system_applications/openssh-server/sshd_config/Port 2222
  registry get system_applications/openssh-server/sshd_config/Port
  registry diff
  registry validate
  registry apply
  registry discard
  registry reset system_applications/openssh-server/sshd_config/Port
  registry view changes
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
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
