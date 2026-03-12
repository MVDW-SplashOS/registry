import sys
import datetime
import shutil
import yaml
from pathlib import Path
from typing import Any

from .base import Command


class BackupListCommand(Command):
    name = "list"
    help = "List available backups"

    def execute(self, args: Any) -> None:
        if not self.core.backup_dir.exists():
            print("No backups found")
            return

        backups = sorted(
            self.core.backup_dir.glob("*.bak"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )

        if not backups:
            print("No backups found")
            return

        print("Available backups:")
        print("=" * 60)
        for backup in backups:
            mtime = backup.stat().st_mtime
            timestamp = datetime.datetime.fromtimestamp(mtime).strftime(
                "%Y-%m-%d %H:%M:%S"
            )
            print(f"  {backup.name}")
            print(f"    Created: {timestamp}")
            print(f"    Path: {backup}")
            print()
        print("=" * 60)


class BackupRestoreCommand(Command):
    name = "restore"
    help = "Restore from a backup"

    def _add_arguments(self, parser):
        parser.add_argument("backup_name", help="Backup name to restore")

    def execute(self, args: Any) -> None:
        backup_name = args.backup_name

        if not self.core.backup_dir.exists():
            print("No backups found")
            sys.exit(1)

        backup_path = self.core.backup_dir / backup_name
        if not backup_path.exists():
            backup_path = self.core.backup_dir / f"{backup_name}.bak"
            if not backup_path.exists():
                print(f"Backup not found: {backup_name}")
                sys.exit(1)

        original_path = self._find_original_path(backup_path.name)

        if not original_path:
            print(f"Could not determine original location for: {backup_path.stem}")
            print(f"Backup file: {backup_path}")
            user_input = input(
                "Enter original file path (or press Enter to cancel): "
            ).strip()
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

    def _find_original_path(self, backup_name: str) -> Path:
        definitions_dir = self.core.get_definitions_dir()
        original_name = Path(backup_name).stem

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
                                        if (
                                            struct_name == original_name
                                            or struct_file == original_name
                                        ):
                                            struct_path = (
                                                pkg_dir / f"{struct_file}.yaml"
                                            )
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


class BackupDeleteCommand(Command):
    name = "delete"
    help = "Delete a backup"

    def _add_arguments(self, parser):
        parser.add_argument("backup_name", help="Backup name to delete")

    def execute(self, args: Any) -> None:
        backup_name = args.backup_name

        backup_path = self.core.backup_dir / backup_name
        if not backup_path.exists():
            backup_path = self.core.backup_dir / f"{backup_name}.bak"
            if not backup_path.exists():
                print(f"Backup not found: {backup_name}")
                sys.exit(1)

        try:
            backup_path.unlink()
            print(f"Deleted backup: {backup_name}")
        except Exception as e:
            print(f"Error deleting backup: {e}")
            sys.exit(1)
