import xml.etree.ElementTree as ET
from typing import Dict, Any, List, Optional
from ....decoder.base import FileTypeDecoder


class XmlDecoder(FileTypeDecoder):
    """Decoder for XML configuration files"""

    def decode(self, file_content: str, structure: Dict[str, Any]) -> Dict[str, Any]:
        """Decode XML file content"""
        try:
            root = ET.fromstring(file_content)
            return self._element_to_dict(root, structure)
        except ET.ParseError as e:
            raise ValueError(f"Invalid XML format: {e}")

    def encode(self, data: Dict[str, Any], structure: Dict[str, Any]) -> str:
        """Encode data back to XML format"""
        root_element = structure.get("root_element", "configuration")
        root = ET.Element(root_element)

        self._dict_to_element(data, root, structure)

        # Format XML output
        indent = structure.get("formatting", {}).get("indent", 2)
        if indent:
            self._indent(root, indent_level=0)

        return ET.tostring(root, encoding="unicode")

    def validate(self, data: Dict[str, Any], structure: Dict[str, Any]) -> List[str]:
        """Validate XML data against structure definition"""
        errors = []

        # Get validation rules from structure
        validation_rules = structure.get("validation", {}).get("rules", [])
        schema = structure.get("schema", {})

        # Validate against schema if provided
        if schema:
            schema_errors = self._validate_against_schema(data, schema)
            errors.extend(schema_errors)

        # Validate custom rules
        for rule in validation_rules:
            rule_errors = self._validate_rule(data, rule)
            errors.extend(rule_errors)

        return errors

    def _element_to_dict(
        self, element: ET.Element, structure: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Convert XML element to dictionary"""
        result = {}

        # Handle attributes
        if element.attrib:
            result["@attributes"] = element.attrib

        # Handle child elements
        for child in element:
            child_tag = child.tag
            child_data = self._element_to_dict(child, structure)

            # Handle multiple elements with same tag
            if child_tag in result:
                if not isinstance(result[child_tag], list):
                    result[child_tag] = [result[child_tag]]
                result[child_tag].append(child_data)
            else:
                result[child_tag] = child_data

        # Handle text content
        if element.text and element.text.strip():
            if result:  # If there are other elements/attributes
                result["#text"] = element.text.strip()
            else:  # If this is a simple text element
                return element.text.strip()

        return result

    def _dict_to_element(
        self, data: Any, parent: ET.Element, structure: Dict[str, Any]
    ):
        """Convert dictionary to XML elements"""
        if isinstance(data, dict):
            for key, value in data.items():
                if key == "@attributes":
                    # Handle attributes
                    for attr_name, attr_value in value.items():
                        parent.set(attr_name, str(attr_value))
                elif key == "#text":
                    # Handle text content
                    parent.text = str(value)
                else:
                    # Handle child elements
                    if isinstance(value, list):
                        # Multiple elements with same tag
                        for item in value:
                            child = ET.SubElement(parent, key)
                            self._dict_to_element(item, child, structure)
                    else:
                        child = ET.SubElement(parent, key)
                        self._dict_to_element(value, child, structure)
        else:
            # Simple value
            parent.text = str(data)

    def _indent(self, elem: ET.Element, indent_level: int):
        """Pretty-print XML with indentation"""
        indent = "  " * indent_level
        if len(elem):
            if not elem.text or not elem.text.strip():
                elem.text = f"\n{indent}  "
            if not elem.tail or not elem.tail.strip():
                elem.tail = f"\n{indent}"
            for child in elem:
                self._indent(child, indent_level + 1)
            if not child.tail or not child.tail.strip():
                child.tail = f"\n{indent}"
        else:
            if indent_level and (not elem.tail or not elem.tail.strip()):
                elem.tail = f"\n{indent}"

    def _validate_against_schema(
        self, data: Dict[str, Any], schema: Dict[str, Any]
    ) -> List[str]:
        """Validate data against XML schema definition"""
        errors = []

        # Check required elements
        required_elements = schema.get("required_elements", [])
        for element in required_elements:
            if element not in data:
                errors.append(f"Required element missing: {element}")

        # Check element types
        element_definitions = schema.get("elements", {})
        for element_name, element_value in data.items():
            if element_name in element_definitions:
                element_def = element_definitions[element_name]
                expected_type = element_def.get("type", "string")

                if expected_type == "string" and not isinstance(element_value, str):
                    errors.append(f"Element {element_name} must be a string")
                elif expected_type == "number" and not isinstance(
                    element_value, (int, float)
                ):
                    errors.append(f"Element {element_name} must be a number")
                elif expected_type == "integer" and not isinstance(element_value, int):
                    errors.append(f"Element {element_name} must be an integer")
                elif expected_type == "boolean" and not isinstance(element_value, bool):
                    errors.append(f"Element {element_name} must be a boolean")

                # Check allowed values for enum types
                if expected_type == "enum":
                    allowed_values = element_def.get("allowed_values", [])
                    if element_value not in allowed_values:
                        errors.append(
                            f"Element {element_name} must be one of: {', '.join(allowed_values)}"
                        )

        return errors

    def _validate_rule(self, data: Dict[str, Any], rule: Dict[str, Any]) -> List[str]:
        """Validate a single custom rule"""
        errors = []
        rule_type = rule.get("type")

        if rule_type == "required_element":
            element = rule.get("element")
            if element not in data:
                errors.append(f"Required element missing: {element}")

        elif rule_type == "element_type":
            element = rule.get("element")
            expected_type = rule.get("expected_type")
            if element in data:
                value = data[element]
                if expected_type == "string" and not isinstance(value, str):
                    errors.append(f"Element {element} must be a string")
                elif expected_type == "number" and not isinstance(value, (int, float)):
                    errors.append(f"Element {element} must be a number")
                elif expected_type == "integer" and not isinstance(value, int):
                    errors.append(f"Element {element} must be an integer")
                elif expected_type == "boolean" and not isinstance(value, bool):
                    errors.append(f"Element {element} must be a boolean")

        elif rule_type == "attribute_required":
            element = rule.get("element")
            attribute = rule.get("attribute")
            if element in data and isinstance(data[element], dict):
                attributes = data[element].get("@attributes", {})
                if attribute not in attributes:
                    errors.append(
                        f"Required attribute {attribute} missing from element {element}"
                    )

        elif rule_type == "pattern":
            import re

            element = rule.get("element")
            pattern = rule.get("pattern")
            if element in data and isinstance(data[element], str):
                if not re.match(pattern, data[element]):
                    errors.append(f"Element {element} must match pattern: {pattern}")

        elif rule_type == "custom":
            # Custom validation function
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
