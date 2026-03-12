import sys
from typing import Any

from .base import Command
from libregistry import decoder


class ValidateCommand(Command):
    name = "validate"
    help = "Validate pending changes against definitions"

    def execute(self, args: Any) -> None:
        changes = self.core.load_changes()

        if not changes:
            print("No pending changes to validate")
            return

        errors = []
        valid_count = 0

        for category, packages in changes.items():
            for package, configs in packages.items():
                for config_path, value in configs.items():
                    try:
                        structure = self.core.get_config_structure(category, package, config_path)
                        config_file = self.core.get_config_file_path(structure)

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
                            validation_errors = filetype_decoder.validate(current_config, encoding_structure)
                            if validation_errors:
                                errors.append(f"{category}/{package}/{config_path}: " + "; ".join(validation_errors))
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


class ValidateConfigCommand(Command):
    name = "validate-config"
    help = "Validate a configuration file against its definition"

    @classmethod
    def _add_arguments(cls, parser):
        parser.add_argument("path", help="Configuration path (category/package/config)")
        parser.add_argument("--strict", action="store_true", help="Enable strict validation")

    def execute(self, args: Any) -> None:
        try:
            path = args.path
            parts = path.split("/")
            if len(parts) < 3:
                print("Invalid path format. Use: category/package/config_path")
                sys.exit(1)

            category = parts[0]
            package = parts[1]
            config_path = "/".join(parts[2:])

            structure = self.core.get_config_structure(category, package, config_path)
            config_file = self.core.get_config_file_path(structure)

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
