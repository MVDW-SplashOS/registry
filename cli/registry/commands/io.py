import sys
import json
import yaml
import datetime
from typing import Any, Optional

from .base import Command


class ExportCommand(Command):
    name = "export"
    help = "Export registry state"

    @classmethod
    def _add_arguments(cls, parser):
        parser.add_argument("--file", "-f", help="Output file path")
        parser.add_argument("--format", choices=["yaml", "json"], default="yaml", help="Export format")

    def execute(self, args: Any) -> None:
        try:
            changes = self.core.load_changes()
            backups = []

            if self.core.backup_dir.exists():
                for backup in self.core.backup_dir.glob("*.bak"):
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

            if args.format == "json":
                output = json.dumps(export_data, indent=2)
            else:
                output = yaml.dump(export_data, default_flow_style=False)

            if args.file:
                with open(args.file, "w") as f:
                    f.write(output)
                print(f"Exported to: {args.file}")
            else:
                print(output)

        except Exception as e:
            print(f"Error exporting: {e}")
            if self.verbose:
                import traceback
                traceback.print_exc()
            sys.exit(1)


class ImportCommand(Command):
    name = "import"
    help = "Import registry state"

    @classmethod
    def _add_arguments(cls, parser):
        parser.add_argument("file", help="Import file path")
        parser.add_argument("--merge", "-m", action="store_true", help="Merge with existing changes")

    def execute(self, args: Any) -> None:
        try:
            file_path = args.file

            with open(file_path, "r") as f:
                if file_path.endswith(".json"):
                    import_data = json.load(f)
                else:
                    import_data = yaml.safe_load(f)

            if "version" not in import_data:
                print("Invalid import file: missing version")
                sys.exit(1)

            imported_changes = import_data.get("changes", {})

            if not args.merge:
                current_changes = {}
            else:
                current_changes = self.core.load_changes()
                for cat, packages in imported_changes.items():
                    if cat not in current_changes:
                        current_changes[cat] = {}
                    for pkg, configs in packages.items():
                        if pkg not in current_changes[cat]:
                            current_changes[cat][pkg] = {}
                        current_changes[cat][pkg].update(configs)

            self.core.save_changes(current_changes)
            print(f"Imported {len(imported_changes)} change(s)")

        except Exception as e:
            print(f"Error importing: {e}")
            if self.verbose:
                import traceback
                traceback.print_exc()
            sys.exit(1)
