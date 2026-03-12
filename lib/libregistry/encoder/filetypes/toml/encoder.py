import sys
import json
from typing import Dict, Any, List

try:
    import tomli_w
    HAS_TOMLI_W = True
except ImportError:
    HAS_TOMLI_W = False

from ....encoder.base import FileTypeEncoder
from ....exceptions import EncodingError


class TomlEncoder(FileTypeEncoder):
    """Encoder for TOML configuration files"""

    def encode(self, data: Dict[str, Any], structure: Dict[str, Any]) -> str:
        """Encode data to TOML format"""
        if HAS_TOMLI_W:
            try:
                return tomli_w.dumps(data)
            except Exception as e:
                raise EncodingError(f"Failed to encode to TOML: {e}")
        else:
            return self._manual_toml_encode(data)

    def _manual_toml_encode(self, data: Dict[str, Any], prefix: str = "") -> str:
        """Manually encode data to TOML format"""
        lines = []
        
        for key, value in data.items():
            if isinstance(value, dict):
                lines.append(f"[{key}]")
                for subkey, subvalue in value.items():
                    formatted_key = self._format_key(subkey)
                    if isinstance(subvalue, bool):
                        lines.append(f"{formatted_key} = {'true' if subvalue else 'false'}")
                    elif isinstance(subvalue, int):
                        lines.append(f"{formatted_key} = {subvalue}")
                    elif isinstance(subvalue, float):
                        lines.append(f"{formatted_key} = {subvalue}")
                    elif isinstance(subvalue, list):
                        list_str = ", ".join(f'"{str(v)}"' for v in subvalue)
                        lines.append(f"{formatted_key} = [{list_str}]")
                    elif subvalue is None:
                        lines.append(f"{formatted_key} = \"\"")
                    else:
                        lines.append(f'{formatted_key} = "{subvalue}"')
            else:
                formatted_key = self._format_key(key)
                if isinstance(value, bool):
                    lines.append(f"{formatted_key} = {'true' if value else 'false'}")
                elif isinstance(value, int):
                    lines.append(f"{formatted_key} = {value}")
                elif isinstance(value, float):
                    lines.append(f"{formatted_key} = {value}")
                elif isinstance(value, list):
                    list_str = ", ".join(f'"{str(v)}"' for v in value)
                    lines.append(f"{formatted_key} = [{list_str}]")
                elif value is None:
                    lines.append(f"{formatted_key} = \"\"")
                else:
                    lines.append(f'{formatted_key} = "{value}"')
        
        return "\n".join(lines)

    def _format_key(self, key: str) -> str:
        """Format a key for TOML (handle special characters)"""
        if any(c in key for c in "- ") or key[0].isdigit():
            return f'"{key}"'
        return key

    def validate_structure(
        self, data: Dict[str, Any], structure: Dict[str, Any]
    ) -> List[str]:
        """Validate data structure before encoding"""
        errors = []

        structures = structure.get("structures", {})

        for section_name, section_data in data.items():
            if section_name in structures:
                section_structure = structures[section_name]
                options = section_structure.get("options", {})

                for key, value in section_data.items():
                    if key in options:
                        option_def = options[key]
                        option_errors = self._validate_option(key, value, option_def)
                        errors.extend(option_errors)
                    else:
                        errors.append(f"Unknown option in {section_name}: {key}")

                for option_name, option_def in options.items():
                    if option_def.get("required", False) and option_name not in section_data:
                        errors.append(f"Required option missing in {section_name}: {option_name}")

        return errors

    def _validate_option(
        self, key: str, value: Any, option_def: Dict[str, Any]
    ) -> List[str]:
        """Validate a single option against its definition"""
        errors = []
        option_type = option_def.get("type", "string")

        if option_type == "boolean":
            if not isinstance(value, bool):
                errors.append(f"Option {key} must be boolean")
        elif option_type == "integer":
            if not isinstance(value, int):
                errors.append(f"Option {key} must be integer")
        elif option_type == "float":
            if not isinstance(value, (int, float)):
                errors.append(f"Option {key} must be a number")
        elif option_type == "string_list":
            if not isinstance(value, list):
                errors.append(f"Option {key} must be a list of strings")
        elif option_type == "enum":
            allowed_values = option_def.get("values", [])
            if value not in allowed_values:
                errors.append(
                    f"Option {key} must be one of: {', '.join(allowed_values)}"
                )

        if option_type == "integer" and isinstance(value, int):
            min_val = option_def.get("min")
            max_val = option_def.get("max")
            if min_val is not None and value < min_val:
                errors.append(f"Option {key} must be >= {min_val}")
            if max_val is not None and value > max_val:
                errors.append(f"Option {key} must be <= {max_val}")

        return errors
