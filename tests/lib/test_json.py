import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "lib"))

from libregistry.encoder.filetypes.json.encoder import JsonEncoder
from libregistry.decoder.filetypes.json.decoder import JsonDecoder


class TestJsonEncoder:
    def setup_method(self):
        self.encoder = JsonEncoder()

    def test_encode_simple_dict(self):
        data = {"key": "value"}
        structure = {"format": "json"}
        result = self.encoder.encode(data, structure)
        assert '"key": "value"' in result

    def test_encode_nested_dict(self):
        data = {"section": {"key": "value"}}
        structure = {"format": "json"}
        result = self.encoder.encode(data, structure)
        assert '"section"' in result
        assert '"key": "value"' in result

    def test_encode_boolean_true(self):
        data = {"enabled": True}
        structure = {"format": "json"}
        result = self.encoder.encode(data, structure)
        assert '"enabled": true' in result

    def test_encode_boolean_false(self):
        data = {"disabled": False}
        structure = {"format": "json"}
        result = self.encoder.encode(data, structure)
        assert '"disabled": false' in result

    def test_encode_integer(self):
        data = {"port": 8080}
        structure = {"format": "json"}
        result = self.encoder.encode(data, structure)
        assert '"port": 8080' in result

    def test_encode_float(self):
        data = {"rate": 3.14}
        structure = {"format": "json"}
        result = self.encoder.encode(data, structure)
        assert '"rate": 3.14' in result

    def test_encode_list(self):
        data = {"servers": ["server1", "server2"]}
        structure = {"format": "json"}
        result = self.encoder.encode(data, structure)
        assert "server1" in result
        assert "server2" in result

    def test_encode_empty_list(self):
        data = {"items": []}
        structure = {"format": "json"}
        result = self.encoder.encode(data, structure)
        assert '"items": []' in result

    def test_encode_null_value(self):
        data = {"key": None}
        structure = {"format": "json"}
        result = self.encoder.encode(data, structure)
        assert '"key": null' in result

    def test_encode_empty_dict(self):
        data = {}
        structure = {"format": "json"}
        result = self.encoder.encode(data, structure)
        assert result == "{}"

    def test_encode_with_custom_indent(self):
        data = {"key": "value"}
        structure = {"format": "json", "formatting": {"indent": 4}}
        result = self.encoder.encode(data, structure)
        assert "    " in result

    def test_encode_with_sort_keys(self):
        data = {"z_key": 1, "a_key": 2}
        structure = {"format": "json", "formatting": {"sort_keys": True}}
        result = self.encoder.encode(data, structure)
        assert result.index("a_key") < result.index("z_key")

    def test_encode_nested_lists(self):
        data = {"matrix": [[1, 2], [3, 4]]}
        structure = {"format": "json"}
        result = self.encoder.encode(data, structure)
        assert "matrix" in result

    def test_encode_unicode(self):
        data = {"message": "hello world"}
        structure = {"format": "json"}
        result = self.encoder.encode(data, structure)
        assert "hello world" in result

    def test_validate_structure_valid(self):
        data = {"main": {"port": 8080}}
        structure = {
            "format": "json",
            "structures": {
                "main": {
                    "options": {
                        "port": {"type": "integer"}
                    }
                }
            }
        }
        errors = self.encoder.validate_structure(data, structure)
        assert len(errors) == 0

    def test_validate_structure_invalid_type(self):
        data = {"main": {"port": "not_an_integer"}}
        structure = {
            "format": "json",
            "structures": {
                "main": {
                    "options": {
                        "port": {"type": "integer"}
                    }
                }
            }
        }
        errors = self.encoder.validate_structure(data, structure)
        assert len(errors) > 0

    def test_validate_structure_unknown_option(self):
        data = {"main": {"unknown_key": "value"}}
        structure = {
            "format": "json",
            "structures": {
                "main": {
                    "options": {}
                }
            }
        }
        errors = self.encoder.validate_structure(data, structure)
        assert any("Unknown option" in err for err in errors)

    def test_validate_structure_required_missing(self):
        data = {"main": {}}
        structure = {
            "format": "json",
            "structures": {
                "main": {
                    "options": {
                        "port": {"type": "integer", "required": True}
                    }
                }
            }
        }
        errors = self.encoder.validate_structure(data, structure)
        assert len(errors) > 0

    def test_validate_enum(self):
        data = {"main": {"status": "invalid"}}
        structure = {
            "format": "json",
            "structures": {
                "main": {
                    "options": {
                        "status": {"type": "enum", "values": ["active", "inactive"]}
                    }
                }
            }
        }
        errors = self.encoder.validate_structure(data, structure)
        assert len(errors) > 0

    def test_validate_enum_valid(self):
        data = {"main": {"status": "active"}}
        structure = {
            "format": "json",
            "structures": {
                "main": {
                    "options": {
                        "status": {"type": "enum", "values": ["active", "inactive"]}
                    }
                }
            }
        }
        errors = self.encoder.validate_structure(data, structure)
        assert len(errors) == 0

    def test_validate_integer_range(self):
        data = {"main": {"port": 99999}}
        structure = {
            "format": "json",
            "structures": {
                "main": {
                    "options": {
                        "port": {"type": "integer", "min": 1, "max": 65535}
                    }
                }
            }
        }
        errors = self.encoder.validate_structure(data, structure)
        assert len(errors) > 0

    def test_validate_integer_range_valid(self):
        data = {"main": {"port": 8080}}
        structure = {
            "format": "json",
            "structures": {
                "main": {
                    "options": {
                        "port": {"type": "integer", "min": 1, "max": 65535}
                    }
                }
            }
        }
        errors = self.encoder.validate_structure(data, structure)
        assert len(errors) == 0

    def test_validate_boolean_type(self):
        data = {"main": {"enabled": "yes"}}
        structure = {
            "format": "json",
            "structures": {
                "main": {
                    "options": {
                        "enabled": {"type": "boolean"}
                    }
                }
            }
        }
        errors = self.encoder.validate_structure(data, structure)
        assert len(errors) > 0

    def test_validate_float_type(self):
        data = {"main": {"rate": "3.14"}}
        structure = {
            "format": "json",
            "structures": {
                "main": {
                    "options": {
                        "rate": {"type": "float"}
                    }
                }
            }
        }
        errors = self.encoder.validate_structure(data, structure)
        assert len(errors) > 0


class TestJsonDecoder:
    def setup_method(self):
        self.decoder = JsonDecoder()

    def test_decode_simple_key_value(self):
        content = '{"key": "value"}'
        structure = {"format": "json"}
        result = self.decoder.decode(content, structure)
        assert result["key"] == "value"

    def test_decode_nested_dict(self):
        content = '{"section": {"key": "value"}}'
        structure = {"format": "json"}
        result = self.decoder.decode(content, structure)
        assert result["section"]["key"] == "value"

    def test_decode_list(self):
        content = '{"servers": ["server1", "server2"]}'
        structure = {"format": "json"}
        result = self.decoder.decode(content, structure)
        assert result["servers"] == ["server1", "server2"]

    def test_decode_empty_list(self):
        content = '{"items": []}'
        structure = {"format": "json"}
        result = self.decoder.decode(content, structure)
        assert result["items"] == []

    def test_decode_boolean_true(self):
        content = '{"enabled": true}'
        structure = {"format": "json"}
        result = self.decoder.decode(content, structure)
        assert result["enabled"] is True

    def test_decode_boolean_false(self):
        content = '{"disabled": false}'
        structure = {"format": "json"}
        result = self.decoder.decode(content, structure)
        assert result["disabled"] is False

    def test_decode_integer(self):
        content = '{"port": 8080}'
        structure = {"format": "json"}
        result = self.decoder.decode(content, structure)
        assert result["port"] == 8080

    def test_decode_float(self):
        content = '{"rate": 3.14}'
        structure = {"format": "json"}
        result = self.decoder.decode(content, structure)
        assert result["rate"] == 3.14

    def test_decode_null(self):
        content = '{"key": null}'
        structure = {"format": "json"}
        result = self.decoder.decode(content, structure)
        assert result["key"] is None

    def test_decode_empty_object(self):
        content = "{}"
        structure = {"format": "json"}
        result = self.decoder.decode(content, structure)
        assert result == {}

    def test_decode_encode_roundtrip(self):
        original_data = {
            "server": {
                "host": "localhost",
                "port": 8080,
                "enabled": True
            }
        }
        structure = {"format": "json"}

        encoded = self.decoder.encode(original_data, structure)
        decoded = self.decoder.decode(encoded, structure)

        assert decoded["server"]["host"] == "localhost"
        assert decoded["server"]["port"] == 8080
        assert decoded["server"]["enabled"] is True

    def test_decode_invalid_json(self):
        content = '{"invalid": json'
        structure = {"format": "json"}
        with pytest.raises(ValueError):
            self.decoder.decode(content, structure)

    def test_decode_malformed_json(self):
        content = "not json at all"
        structure = {"format": "json"}
        with pytest.raises(ValueError):
            self.decoder.decode(content, structure)

    def test_validate_against_schema_required_fields(self):
        data = {"name": "test"}
        structure = {
            "format": "json",
            "schema": {
                "required": ["name", "version"]
            }
        }
        errors = self.decoder.validate(data, structure)
        assert len(errors) > 0

    def test_validate_against_schema_required_fields_met(self):
        data = {"name": "test", "version": "1.0"}
        structure = {
            "format": "json",
            "schema": {
                "required": ["name", "version"]
            }
        }
        errors = self.decoder.validate(data, structure)
        assert len(errors) == 0

    def test_validate_against_schema_field_types(self):
        data = {"count": "not_an_integer"}
        structure = {
            "format": "json",
            "schema": {
                "properties": {
                    "count": {"type": "integer"}
                }
            }
        }
        errors = self.decoder.validate(data, structure)
        assert len(errors) > 0

    def test_validate_rule_required(self):
        data = {"name": "test"}
        structure = {
            "format": "json",
            "validation": {
                "rules": [
                    {"type": "required", "field": "version"}
                ]
            }
        }
        errors = self.decoder.validate(data, structure)
        assert len(errors) > 0

    def test_validate_rule_type(self):
        data = {"count": "not_an_int"}
        structure = {
            "format": "json",
            "validation": {
                "rules": [
                    {"type": "type", "field": "count", "expected_type": "integer"}
                ]
            }
        }
        errors = self.decoder.validate(data, structure)
        assert len(errors) > 0

    def test_validate_rule_range(self):
        data = {"port": 99999}
        structure = {
            "format": "json",
            "validation": {
                "rules": [
                    {"type": "range", "field": "port", "min": 1, "max": 65535}
                ]
            }
        }
        errors = self.decoder.validate(data, structure)
        assert len(errors) > 0

    def test_validate_rule_enum(self):
        data = {"status": "unknown"}
        structure = {
            "format": "json",
            "validation": {
                "rules": [
                    {"type": "enum", "field": "status", "allowed_values": ["active", "inactive"]}
                ]
            }
        }
        errors = self.decoder.validate(data, structure)
        assert len(errors) > 0

    def test_validate_rule_pattern(self):
        data = {"email": "invalid-email"}
        structure = {
            "format": "json",
            "validation": {
                "rules": [
                    {"type": "pattern", "field": "email", "pattern": r"^[\w\.-]+@[\w\.-]+\.\w+$"}
                ]
            }
        }
        errors = self.decoder.validate(data, structure)
        assert len(errors) > 0

    def test_validate_rule_pattern_valid(self):
        data = {"email": "test@example.com"}
        structure = {
            "format": "json",
            "validation": {
                "rules": [
                    {"type": "pattern", "field": "email", "pattern": r"^[\w\.-]+@[\w\.-]+\.\w+$"}
                ]
            }
        }
        errors = self.decoder.validate(data, structure)
        assert len(errors) == 0

    def test_validate_multiple_rules(self):
        data = {"port": 80}
        structure = {
            "format": "json",
            "validation": {
                "rules": [
                    {"type": "range", "field": "port", "min": 1, "max": 65535},
                    {"type": "required", "field": "name"}
                ]
            }
        }
        errors = self.decoder.validate(data, structure)
        assert len(errors) > 0

    def test_validate_no_schema_no_rules(self):
        data = {"key": "value"}
        structure = {"format": "json"}
        errors = self.decoder.validate(data, structure)
        assert errors == []
