import sys
from typing import Any

from .base import Command
from libregistry import decoder, encoder, File


class ApplyCommand(Command):
    name = "apply"
    help = "Apply all pending changes"

    def execute(self, args: Any) -> None:
        changes = self.core.load_changes()
        if not changes:
            print("No changes to apply")
            return

        permission_issues = self.core.check_permissions(changes)
        if permission_issues:
            print(f"\n{len(permission_issues)} change(s) require elevated privileges:")
            for issue in permission_issues:
                print(f"  - {issue}")
            print("\nThese changes require elevated privileges.")
            print("Please run the following command to apply them:")
            import shutil
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
                        backup_info = self._apply_single_change(category, package, config_path, value)
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
            self.core.save_changes({})
            print(f"Applied {applied_count} change(s)")
        else:
            print("No changes were successfully applied")

    def _rollback_changes(self, backups: list):
        for backup_info in backups:
            config_file = backup_info["config_file"]
            backup_path = backup_info["backup_path"]
            try:
                if backup_path.exists():
                    import shutil
                    shutil.copy2(backup_path, config_file)
                    if self.verbose:
                        print(f"Rolled back: {config_file}")
            except Exception as e:
                print(f"Failed to rollback {config_file}: {e}")

    def _apply_single_change(self, category: str, package: str, config_path: str, value: Any) -> dict:
        import os
        import shutil
        backup_info = None
        try:
            structure = self.core.get_config_structure(category, package, config_path)
            config_file = self.core.get_config_file_path(structure)

            if config_file.exists() and os.access(config_file.parent, os.W_OK):
                import os as _os
                backup_path = self.core.backup_dir / f"{config_file.name}.{_os.getpid()}.bak"
                try:
                    shutil.copy2(config_file, backup_path)
                    backup_info = {"config_file": config_file, "backup_path": backup_path}
                except (PermissionError, OSError) as e:
                    if self.verbose:
                        print(f"Warning: Could not create backup for {config_file}: {e}")

            if config_file.exists():
                current_config = decoder.decode_file(str(config_file), structure)
            else:
                current_config = {}

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

            file_info = structure.get("file", {})
            format_type = file_info.get("format", "key-value")
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


class DiscardCommand(Command):
    name = "discard"
    help = "Discard all pending changes"

    def execute(self, args: Any) -> None:
        changes = self.core.load_changes()
        if not changes:
            print("No changes to discard")
            return

        change_count = sum(len(configs) for packages in changes.values() for configs in packages.values())
        self.core.save_changes({})
        print(f"Discarded {change_count} pending change(s)")


class ViewChangesCommand(Command):
    name = "view-changes"
    help = "View pending changes"

    def execute(self, args: Any) -> None:
        changes = self.core.load_changes()
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
        total_changes = sum(len(configs) for packages in changes.values() for configs in packages.values())
        print(f"Total: {total_changes} change(s) pending")


class DiffCommand(Command):
    name = "diff"
    help = "Show diff between current config and pending changes"

    def execute(self, args: Any) -> None:
        changes = self.core.load_changes()
        if not changes:
            print("No pending changes to show")
            return

        print("Pending changes (diff):")
        print("=" * 60)
        for category, packages in changes.items():
            for package, configs in packages.items():
                for config_path, new_value in configs.items():
                    try:
                        structure = self.core.get_config_structure(category, package, config_path)
                        config_file = self.core.get_config_file_path(structure)

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
