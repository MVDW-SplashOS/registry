import xml.etree.ElementTree as ET
from typing import Dict, Any, List
from ....encoder.base import FileTypeEncoder


class XmlEncoder(FileTypeEncoder):
    """Encoder for XML configuration files"""

    def encode(self, data: Dict[str, Any], structure: Dict[str, Any]) -> str:
        """Encode data to XML format"""
        root_element = structure.get("root_element", "configuration")
        root = ET.Element(root_element)

        self._dict_to_element(data, root)

        indent = structure.get("formatting", {}).get("indent", 2)
        if indent:
            self._indent(root, indent_level=0)

        return ET.tostring(root, encoding="unicode")

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

        return errors

    def _dict_to_element(self, data: Any, parent: ET.Element):
        """Convert dictionary to XML elements"""
        if isinstance(data, dict):
            for key, value in data.items():
                if key == "@attributes":
                    for attr_name, attr_value in value.items():
                        parent.set(attr_name, str(attr_value))
                elif key == "#text":
                    parent.text = str(value)
                else:
                    child = ET.SubElement(parent, key)
                    self._dict_to_element(value, child)
        elif isinstance(data, list):
            for item in data:
                self._dict_to_element(item, parent)
        else:
            parent.text = str(data)

    def _indent(self, elem: ET.Element, indent_level: int = 0, indent_str: str = "  "):
        """Add indentation to XML elements"""
        indent = "\n" + indent_str * indent_level
        if len(elem):
            if not (elem.text and elem.text.strip()):
                elem.text = indent + indent_str
            for child in elem:
                self._indent(child, indent_level + 1, indent_str)
                if not (child.tail and child.tail.strip()):
                    child.tail = indent + indent_str
            if not (child.tail and child.tail.strip()):
                child.tail = indent
        else:
            if indent_level > 0 and not (elem.tail and elem.tail.strip()):
                elem.tail = indent
