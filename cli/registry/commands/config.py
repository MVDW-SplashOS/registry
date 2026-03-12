import sys
from typing import Any

from .base import Command
from libregistry import decoder


class SetCommand(Command):
    name = "set"
    help = "Set a configuration value"

    @classmethod
    def _add_arguments(cls, parser):
        parser.add_argument("path", help="Configuration path (category/package/config/option)")
        parser.add_argument("value", help="Value to set")

    def execute(self, args: Any) -> None:
        try:
            path = args.path
            value = args.value

            category, package, config_path = self.core.parse_path(path)
            parsed_value = self.core.parse_value(value)

            try:
                self.core.get_config_structure(category, package, config_path)
            except Exception as e:
                if self.verbose:
                    raise
                print(f"Warning: Could not validate structure for {path}: {e}")

            changes = self.core.load_changes()

            if category not in changes:
                changes[category] = {}
            if package not in changes[category]:
                changes[category][package] = {}
            if config_path not in changes[category][package]:
                changes[category][package][config_path] = {}

            changes[category][package][config_path] = parsed_value
            self.core.save_changes(changes)
            print(f"Set {path} = {parsed_value}")

        except Exception as e:
            print(f"Error setting value: {e}")
            if self.verbose:
                import traceback
                traceback.print_exc()
            sys.exit(1)


class GetCommand(Command):
    name = "get"
    help = "Get a configuration value"

    @classmethod
    def _add_arguments(cls, parser):
        parser.add_argument("path", help="Configuration path (category/package/config/option)")

    def execute(self, args: Any) -> None:
        try:
            path = args.path
            category, package, config_path = self.core.parse_path(path)

            structure = self.core.get_config_structure(category, package, config_path)
            config_file = self.core.get_config_file_path(structure)

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


class ResetCommand(Command):
    name = "reset"
    help = "Reset a configuration to its default"

    @classmethod
    def _add_arguments(cls, parser):
        parser.add_argument("path", help="Configuration path to reset")

    def execute(self, args: Any) -> None:
        try:
            path = args.path
            category, package, config_path = self.core.parse_path(path)

            changes = self.core.load_changes()

            if category in changes and package in changes[category] and config_path in changes[category][package]:
                del changes[category][package][config_path]

                if not changes[category][package]:
                    del changes[category][package]
                if not changes[category]:
                    del changes[category]

                self.core.save_changes(changes)
                print(f"Reset {path}")
            else:
                print(f"No pending changes for {path}")

        except Exception as e:
            print(f"Error resetting configuration: {e}")
            sys.exit(1)
