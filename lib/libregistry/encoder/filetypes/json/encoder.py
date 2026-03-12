import json
from typing import Dict, Any, List
from ....encoder.base import FileTypeEncoder


class JsonEncoder(FileTypeEncoder):
    """Encoder for JSON configuration files"""

    def encode(self, data: Dict[str, Any], structure: Dict[str, Any]) -> str:
        """Encode data to JSON format"""
        indent = structure.get("formatting", {}).get("indent", 2)
        sort_keys = structure.get("formatting", {}).get("sort_keys", False)

        return json.dumps(data, indent=indent, sort_keys=sort_keys, ensure_ascii=False)

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
                    if (
                        option_def.get("required", False)
                        and option_name not in section_data
                    ):
                        errors.append(
                            f"Required option missing in {section_name}: {option_name}"
                        )

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
        elif option_type == "array":
            if not isinstance(value, list):
                errors.append(f"Option {key} must be an array")
        elif option_type == "object":
            if not isinstance(value, dict):
                errors.append(f"Option {key} must be an object")
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
