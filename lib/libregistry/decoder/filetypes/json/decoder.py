import json
from typing import Dict, Any, List
from ....decoder.base import FileTypeDecoder


class JsonDecoder(FileTypeDecoder):
    """Decoder for JSON configuration files"""

    def decode(self, file_content: str, structure: Dict[str, Any]) -> Dict[str, Any]:
        """Decode JSON file content"""
        try:
            return json.loads(file_content)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON format: {e}")

    def encode(self, data: Dict[str, Any], structure: Dict[str, Any]) -> str:
        """Encode data back to JSON format"""
        indent = structure.get("formatting", {}).get("indent", 2)
        sort_keys = structure.get("formatting", {}).get("sort_keys", False)

        return json.dumps(data, indent=indent, sort_keys=sort_keys, ensure_ascii=False)

    def validate(self, data: Dict[str, Any], structure: Dict[str, Any]) -> List[str]:
        """Validate JSON data against structure definition"""
        errors = []

        # Get validation rules from structure
        validation_rules = structure.get("validation", {}).get("rules", [])
        schema = structure.get("schema", {})

        # Validate against JSON schema if provided
        if schema:
            schema_errors = self._validate_against_schema(data, schema)
            errors.extend(schema_errors)

        # Validate custom rules
        for rule in validation_rules:
            rule_errors = self._validate_rule(data, rule)
            errors.extend(rule_errors)

        return errors

    def _validate_against_schema(
        self, data: Dict[str, Any], schema: Dict[str, Any]
    ) -> List[str]:
        """Validate data against JSON schema"""
        errors = []

        # Simple schema validation (for basic cases)
        # In a real implementation, you might use jsonschema library

        # Check required fields
        required_fields = schema.get("required", [])
        for field in required_fields:
            if field not in data:
                errors.append(f"Required field missing: {field}")

        # Check field types
        properties = schema.get("properties", {})
        for field_name, field_value in data.items():
            if field_name in properties:
                field_schema = properties[field_name]
                expected_type = field_schema.get("type")

                if expected_type == "string" and not isinstance(field_value, str):
                    errors.append(f"Field {field_name} must be a string")
                elif expected_type == "number" and not isinstance(
                    field_value, (int, float)
                ):
                    errors.append(f"Field {field_name} must be a number")
                elif expected_type == "integer" and not isinstance(field_value, int):
                    errors.append(f"Field {field_name} must be an integer")
                elif expected_type == "boolean" and not isinstance(field_value, bool):
                    errors.append(f"Field {field_name} must be a boolean")
                elif expected_type == "array" and not isinstance(field_value, list):
                    errors.append(f"Field {field_name} must be an array")
                elif expected_type == "object" and not isinstance(field_value, dict):
                    errors.append(f"Field {field_name} must be an object")

        return errors

    def _validate_rule(self, data: Dict[str, Any], rule: Dict[str, Any]) -> List[str]:
        """Validate a single custom rule"""
        errors = []
        rule_type = rule.get("type")

        if rule_type == "required":
            field = rule.get("field")
            if field not in data:
                errors.append(f"Required field missing: {field}")

        elif rule_type == "type":
            field = rule.get("field")
            expected_type = rule.get("expected_type")
            if field in data:
                value = data[field]
                if expected_type == "string" and not isinstance(value, str):
                    errors.append(f"Field {field} must be a string")
                elif expected_type == "number" and not isinstance(value, (int, float)):
                    errors.append(f"Field {field} must be a number")
                elif expected_type == "integer" and not isinstance(value, int):
                    errors.append(f"Field {field} must be an integer")
                elif expected_type == "boolean" and not isinstance(value, bool):
                    errors.append(f"Field {field} must be a boolean")

        elif rule_type == "range":
            field = rule.get("field")
            if field in data:
                value = data[field]
                if isinstance(value, (int, float)):
                    min_val = rule.get("min")
                    max_val = rule.get("max")
                    if min_val is not None and value < min_val:
                        errors.append(f"Field {field} must be >= {min_val}")
                    if max_val is not None and value > max_val:
                        errors.append(f"Field {field} must be <= {max_val}")

        elif rule_type == "enum":
            field = rule.get("field")
            allowed_values = rule.get("allowed_values", [])
            if field in data and data[field] not in allowed_values:
                errors.append(
                    f"Field {field} must be one of: {', '.join(map(str, allowed_values))}"
                )

        elif rule_type == "pattern":
            import re

            field = rule.get("field")
            pattern = rule.get("pattern")
            if field in data and isinstance(data[field], str):
                if not re.match(pattern, data[field]):
                    errors.append(f"Field {field} must match pattern: {pattern}")

        elif rule_type == "custom":
            # Custom validation function (would need to be implemented)
            validator = rule.get("validator")
            if validator:
                try:
                    result = validator(data)
                    if not result:
                        errors.append(rule.get("message", "Custom validation failed"))
                except Exception as e:
                    errors.append(
                        f"Custom validation error for {rule.get('name', 'unknown')}: {e}"
                    )

        return errors
