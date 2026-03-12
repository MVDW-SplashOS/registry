import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "lib"))

from .core.registry import RegistryCore as _RegistryCore


class RegistryCLI:
    """Backwards compatible CLI class for registry operations."""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self._core = _RegistryCore(verbose=verbose)

    def __getattr__(self, name):
        if name in ("changes_file", "backup_dir"):
            return getattr(self._core, name)
        if name == "_parse_path":
            return self._core.parse_path
        if name == "parse_path":
            return self._core.parse_path
        raise AttributeError(
            f"'{type(self).__name__}' object has no attribute '{name}'"
        )

    def __setattr__(self, name, value):
        if name in ("changes_file", "backup_dir"):
            object.__setattr__(self._core, name, value)
        else:
            object.__setattr__(self, name, value)

    def set_command(self, path: str, value: str):
        from .commands import SetCommand

        cmd = SetCommand(self._core)
        cmd.execute(type("Args", (), {"path": path, "value": value})())

    def apply_command(self):
        from .commands import ApplyCommand

        ApplyCommand(self._core).execute(type("Args", (), {})())

    def discard_command(self):
        from .commands import DiscardCommand

        DiscardCommand(self._core).execute(type("Args", (), {})())

    def reset_command(self, path: str):
        from .commands import ResetCommand

        ResetCommand(self._core).execute(type("Args", (), {"path": path})())

    def view_changes_command(self):
        from .commands import ViewChangesCommand

        ViewChangesCommand(self._core).execute(type("Args", (), {})())

    def get_command(self, path: str):
        from .commands import GetCommand

        GetCommand(self._core).execute(type("Args", (), {"path": path})())

    def diff_command(self):
        from .commands import DiffCommand

        DiffCommand(self._core).execute(type("Args", (), {})())

    def validate_command(self):
        from .commands import ValidateCommand

        ValidateCommand(self._core).execute(type("Args", (), {})())

    def validate_config_command(self, path: str, strict: bool = False):
        from .commands import ValidateConfigCommand

        ValidateConfigCommand(self._core).execute(
            type("Args", (), {"path": path, "strict": strict})()
        )

    def list_command(self, category: str = None, detected_only: bool = False):
        from .commands import ListCommand

        ListCommand(self._core).execute(
            type("Args", (), {"category": category, "detected": detected_only})()
        )

    def search_command(self, query: str):
        from .commands import SearchCommand

        SearchCommand(self._core).execute(type("Args", (), {"query": query})())

    def info_command(self, package: str):
        from .commands import InfoCommand

        InfoCommand(self._core).execute(type("Args", (), {"package": package})())

    def detect_command(self, package: str = None):
        from .commands import DetectCommand

        DetectCommand(self._core).execute(type("Args", (), {"package": package})())

    def export_command(self, file_path: str = None, format: str = "yaml"):
        from .commands import ExportCommand

        ExportCommand(self._core).execute(
            type("Args", (), {"file": file_path, "format": format})()
        )

    def import_command(self, file_path: str, merge: bool = False):
        from .commands import ImportCommand

        ImportCommand(self._core).execute(
            type("Args", (), {"file": file_path, "merge": merge})()
        )

    def backup_list_command(self):
        from .commands import BackupListCommand

        BackupListCommand(self._core).execute(type("Args", (), {})())

    def backup_restore_command(self, backup_name: str):
        from .commands import BackupRestoreCommand

        BackupRestoreCommand(self._core).execute(
            type("Args", (), {"backup_name": backup_name})()
        )

    def backup_delete_command(self, backup_name: str):
        from .commands import BackupDeleteCommand

        BackupDeleteCommand(self._core).execute(
            type("Args", (), {"backup_name": backup_name})()
        )

    def _ensure_directories(self):
        pass


from .core.registry import RegistryCore
from .commands import (
    SetCommand,
    GetCommand,
    ResetCommand,
    ApplyCommand,
    DiscardCommand,
    ViewChangesCommand,
    DiffCommand,
    ValidateCommand,
    ValidateConfigCommand,
    ListCommand,
    SearchCommand,
    InfoCommand,
    DetectCommand,
    BackupListCommand,
    BackupRestoreCommand,
    BackupDeleteCommand,
    ExportCommand,
    ImportCommand,
)


def main():
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
  registry view-changes
  registry list
  registry search openssh
  registry info system_applications/openssh-server
  registry detect
  registry export --file backup.yaml
  registry import backup.yaml
        """,
    )

    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose output"
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    commands = [
        SetCommand,
        GetCommand,
        ResetCommand,
        ApplyCommand,
        DiscardCommand,
        ViewChangesCommand,
        DiffCommand,
        ValidateCommand,
        ValidateConfigCommand,
        ListCommand,
        SearchCommand,
        InfoCommand,
        DetectCommand,
        ExportCommand,
        ImportCommand,
    ]

    for cmd_class in commands:
        cmd_class.add_parser(subparsers)

    backup_subparsers = subparsers.add_parser("backup", help="Backup operations")
    backup_subparsers.add_argument(
        "action", choices=["list", "restore", "delete"], help="Backup action"
    )
    backup_subparsers.add_argument(
        "backup_name", nargs="?", help="Backup name (for restore/delete)"
    )

    args = parser.parse_args()

    core = RegistryCore(verbose=args.verbose)

    if args.command == "set":
        SetCommand(core).execute(args)
    elif args.command == "get":
        GetCommand(core).execute(args)
    elif args.command == "reset":
        ResetCommand(core).execute(args)
    elif args.command == "apply":
        ApplyCommand(core).execute(args)
    elif args.command == "discard":
        DiscardCommand(core).execute(args)
    elif args.command == "view-changes":
        ViewChangesCommand(core).execute(args)
    elif args.command == "diff":
        DiffCommand(core).execute(args)
    elif args.command == "validate":
        ValidateCommand(core).execute(args)
    elif args.command == "validate-config":
        ValidateConfigCommand(core).execute(args)
    elif args.command == "list":
        ListCommand(core).execute(args)
    elif args.command == "search":
        SearchCommand(core).execute(args)
    elif args.command == "info":
        InfoCommand(core).execute(args)
    elif args.command == "detect":
        DetectCommand(core).execute(args)
    elif args.command == "backup":
        if args.action == "list":
            BackupListCommand(core).execute(args)
        elif args.action == "restore" and args.backup_name:
            BackupRestoreCommand(core).execute(args)
        elif args.action == "delete" and args.backup_name:
            BackupDeleteCommand(core).execute(args)
        else:
            print("Usage: registry backup list")
            sys.exit(1)
    elif args.command == "export":
        ExportCommand(core).execute(args)
    elif args.command == "import":
        ImportCommand(core).execute(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
