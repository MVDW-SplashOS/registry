import re
from typing import Dict, Any, List, Optional
from ....decoder.base import FileTypeDecoder


class KeyValueDecoder(FileTypeDecoder):
    """Decoder for key-value configuration files (like .conf, .ini, .cfg)"""

    def __init__(self):
        self.comment_char = "#"
        self.delimiter = "="
        self.line_continuation = "\\"
        self.case_sensitive = False
        self.quote_values = False

    def decode(self, file_content: str, structure: Dict[str, Any]) -> Dict[str, Any]:
        """Decode key-value file content"""
        lines = file_content.split("\n")
        result = {}
        current_section = "main"
        result[current_section] = {}

        i = 0
        while i < len(lines):
            line = lines[i].strip()

            # Skip empty lines and comments
            if not line or line.startswith(self.comment_char):
                i += 1
                continue

            # Handle line continuation
            while line.endswith(self.line_continuation) and i + 1 < len(lines):
                i += 1
                next_line = lines[i].strip()
                line = line[:-1] + next_line

            # Parse key-value pair
            if self.delimiter in line:
                key, value = self._parse_key_value(line)
                if key:
                    result[current_section][key] = value
            else:
                # Handle sections or other directives
                section_match = self._parse_section(line)
                if section_match:
                    current_section = section_match
                    if current_section not in result:
                        result[current_section] = {}

            i += 1

        return result

    def encode(self, data: Dict[str, Any], structure: Dict[str, Any]) -> str:
        """Encode data back to key-value format"""
        lines = []

        # Get syntax rules from structure
        syntax = structure.get("syntax", {})
        self.comment_char = syntax.get("comment_char", "#")
        self.delimiter = syntax.get("delimiter", "=")
        self.line_continuation = syntax.get("line_continuation", "\\")
        self.case_sensitive = syntax.get("case_sensitive", False)
        self.quote_values = syntax.get("quote_values", False)

        # Handle main section
        main_data = data.get("main", {})
        for key, value in main_data.items():
            line = self._format_key_value(key, value)
            lines.append(line)

        # Handle other sections
        for section_name, section_data in data.items():
            if section_name != "main" and section_data:
                lines.append("")  # Empty line before section
                lines.append(f"[{section_name}]")
                for key, value in section_data.items():
                    line = self._format_key_value(key, value)
                    lines.append(line)

        return "\n".join(lines)

    def validate(self, data: Dict[str, Any], structure: Dict[str, Any]) -> List[str]:
        """Validate key-value data against structure definition"""
        errors = []

        structures = structure.get("structures", {})
        main_structure = structures.get("main", {})

        if not main_structure:
            return errors

        options = main_structure.get("options", {})

        # Validate each option
        main_data = data.get("main", {})
        for key, value in main_data.items():
            if key in options:
                option_def = options[key]
                option_errors = self._validate_option(key, value, option_def)
                errors.extend(option_errors)
            else:
                # Option not defined in structure
                errors.append(f"Unknown option: {key}")

        # Check required options
        for option_name, option_def in options.items():
            if option_def.get("required", False) and option_name not in main_data:
                errors.append(f"Required option missing: {option_name}")

        # Check dependencies
        dependencies = main_structure.get("dependencies", {})
        for option_name, dep_def in dependencies.items():
            if option_name in main_data:
                if "requires" in dep_def:
                    required_option = dep_def["requires"]
                    if required_option not in main_data:
                        errors.append(
                            f"Option {option_name} requires {required_option}"
                        )

                if "incompatible_with" in dep_def:
                    incompatible_option = dep_def["incompatible_with"]
                    if incompatible_option in main_data:
                        errors.append(
                            f"Option {option_name} is incompatible with {incompatible_option}"
                        )

        # Check mutually exclusive options
        mutually_exclusive = main_structure.get("mutually_exclusive", [])
        for group in mutually_exclusive:
            present_options = [opt for opt in group if opt in main_data]
            if len(present_options) > 1:
                errors.append(
                    f"Mutually exclusive options used together: {', '.join(present_options)}"
                )

        return errors

    def _parse_key_value(self, line: str) -> tuple:
        """Parse a single key-value line"""
        # Split on first occurrence of delimiter
        parts = line.split(self.delimiter, 1)
        if len(parts) != 2:
            return None, None

        key = parts[0].strip()
        value = parts[1].strip()

        # Remove quotes if present
        if (value.startswith('"') and value.endswith('"')) or (
            value.startswith("'") and value.endswith("'")
        ):
            value = value[1:-1]

        # Handle boolean values
        if value.lower() in ["yes", "true", "on", "1"]:
            value = True
        elif value.lower() in ["no", "false", "off", "0"]:
            value = False
        # Handle numeric values
        elif value.isdigit():
            value = int(value)

        return key, value

    def _parse_section(self, line: str) -> Optional[str]:
        """Parse section headers like [section]"""
        section_match = re.match(r"^\[([^\]]+)\]$", line)
        if section_match:
            return section_match.group(1)
        return None

    def _format_key_value(self, key: str, value: Any) -> str:
        """Format a key-value pair for output"""
        if isinstance(value, bool):
            value_str = "yes" if value else "no"
        elif isinstance(value, (int, float)):
            value_str = str(value)
        elif isinstance(value, list):
            value_str = " ".join(str(v) for v in value)
        else:
            value_str = str(value)

        if self.quote_values or " " in value_str:
            value_str = f'"{value_str}"'

        return f"{key}{self.delimiter}{value_str}"

    def _validate_option(
        self, key: str, value: Any, option_def: Dict[str, Any]
    ) -> List[str]:
        """Validate a single option against its definition"""
        errors = []
        option_type = option_def.get("type", "string")

        # Type validation
        if option_type == "boolean":
            if not isinstance(value, bool):
                errors.append(f"Option {key} must be boolean")
        elif option_type == "integer":
            if not isinstance(value, int):
                errors.append(f"Option {key} must be integer")
        elif option_type == "string_list":
            if not isinstance(value, list):
                errors.append(f"Option {key} must be a list of strings")
        elif option_type == "enum":
            allowed_values = option_def.get("values", [])
            if value not in allowed_values:
                errors.append(
                    f"Option {key} must be one of: {', '.join(allowed_values)}"
                )

        # Range validation for integers
        if option_type == "integer" and isinstance(value, int):
            min_val = option_def.get("min")
            max_val = option_def.get("max")
            if min_val is not None and value < min_val:
                errors.append(f"Option {key} must be >= {min_val}")
            if max_val is not None and value > max_val:
                errors.append(f"Option {key} must be <= {max_val}")

        return errors
