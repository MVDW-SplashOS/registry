import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "lib"))

from libregistry.encoder.encoder import encoder as global_encoder
from libregistry.decoder.decoder import decoder as global_decoder

KeyValueEncoder = type(global_encoder.get_filetype_encoder("key-value"))
KeyValueDecoder = type(global_decoder.get_filetype_decoder("key-value"))


class TestKeyValueEncoder:
    def setup_method(self):
        self.encoder = KeyValueEncoder()

    def test_encode_simple_key_value(self):
        data = {"main": {"key": "value"}}
        structure = {"format": "key-value"}
        result = self.encoder.encode(data, structure)
        assert "key=value" in result

    def test_encode_with_sections(self):
        data = {
            "main": {"host": "localhost"},
            "database": {"port": 5432}
        }
        structure = {"format": "key-value"}
        result = self.encoder.encode(data, structure)
        assert "[database]" in result
        assert "port=5432" in result

    def test_encode_boolean_yes_no(self):
        data = {"main": {"enabled": True, "disabled": False}}
        structure = {"format": "key-value"}
        result = self.encoder.encode(data, structure)
        assert "enabled=yes" in result
        assert "disabled=no" in result

    def test_encode_integer(self):
        data = {"main": {"port": 8080}}
        structure = {"format": "key-value"}
        result = self.encoder.encode(data, structure)
        assert "port=8080" in result

    def test_encode_float(self):
        data = {"main": {"rate": 3.14}}
        structure = {"format": "key-value"}
        result = self.encoder.encode(data, structure)
        assert "rate=3.14" in result

    def test_encode_list_space_separated(self):
        data = {"main": {"servers": ["server1", "server2"]}}
        structure = {"format": "key-value"}
        result = self.encoder.encode(data, structure)
        assert "server1 server2" in result

    def test_encode_quoted_value(self):
        data = {"main": {"message": "hello world"}}
        structure = {"format": "key-value"}
        result = self.encoder.encode(data, structure)
        assert '"hello world"' in result

    def test_encode_custom_delimiter(self):
        data = {"main": {"key": "value"}}
        structure = {"format": "key-value", "syntax": {"delimiter": ":"}}
        result = self.encoder.encode(data, structure)
        assert "key:value" in result

    def test_encode_custom_comment_char(self):
        data = {"main": {"key": "value"}}
        structure = {"format": "key-value", "syntax": {"comment_char": ";"}}
        result = self.encoder.encode(data, structure)
        assert "key=value" in result

    def test_encode_empty_value(self):
        data = {"main": {"key": ""}}
        structure = {"format": "key-value"}
        result = self.encoder.encode(data, structure)
        assert "key=" in result

    def test_encode_no_quote_spaces_disabled(self):
        data = {"main": {"key": "value"}}
        structure = {"format": "key-value", "syntax": {"quote_values": False}}
        result = self.encoder.encode(data, structure)
        assert "key=value" in result
        assert '"' not in result

    def test_validate_structure_valid(self):
        data = {"main": {"port": 8080}}
        structure = {
            "format": "key-value",
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

    def test_validate_structure_unknown_option(self):
        data = {"main": {"unknown_key": "value"}}
        structure = {
            "format": "key-value",
            "structures": {
                "main": {
                    "options": {}
                }
            }
        }
        errors = self.encoder.validate_structure(data, structure)
        assert len(errors) > 0

    def test_validate_structure_required_missing(self):
        data = {"main": {}}
        structure = {
            "format": "key-value",
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

    def test_validate_dependencies_requires(self):
        data = {"main": {"option_a": "value"}}
        structure = {
            "format": "key-value",
            "structures": {
                "main": {
                    "options": {
                        "option_a": {"type": "string"},
                        "option_b": {"type": "string"}
                    },
                    "dependencies": {
                        "option_a": {"requires": "option_b"}
                    }
                }
            }
        }
        errors = self.encoder.validate_structure(data, structure)
        assert len(errors) > 0

    def test_validate_dependencies_incompatible_with(self):
        data = {"main": {"option_a": "value", "option_b": "value"}}
        structure = {
            "format": "key-value",
            "structures": {
                "main": {
                    "options": {
                        "option_a": {"type": "string"},
                        "option_b": {"type": "string"}
                    },
                    "dependencies": {
                        "option_a": {"incompatible_with": "option_b"}
                    }
                }
            }
        }
        errors = self.encoder.validate_structure(data, structure)
        assert len(errors) > 0

    def test_validate_mutually_exclusive(self):
        data = {"main": {"option_a": "value", "option_b": "value"}}
        structure = {
            "format": "key-value",
            "structures": {
                "main": {
                    "options": {
                        "option_a": {"type": "string"},
                        "option_b": {"type": "string"}
                    },
                    "mutually_exclusive": [["option_a", "option_b"]]
                }
            }
        }
        errors = self.encoder.validate_structure(data, structure)
        assert len(errors) > 0

    def test_validate_boolean_type(self):
        data = {"main": {"enabled": "yes"}}
        structure = {
            "format": "key-value",
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

    def test_validate_integer_type(self):
        data = {"main": {"port": "not_an_int"}}
        structure = {
            "format": "key-value",
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

    def test_validate_string_list_type(self):
        data = {"main": {"servers": "not_a_list"}}
        structure = {
            "format": "key-value",
            "structures": {
                "main": {
                    "options": {
                        "servers": {"type": "string_list"}
                    }
                }
            }
        }
        errors = self.encoder.validate_structure(data, structure)
        assert len(errors) > 0


class TestKeyValueDecoder:
    def setup_method(self):
        self.decoder = KeyValueDecoder()

    def test_decode_simple_key_value(self):
        content = "key=value"
        structure = {"format": "key-value"}
        result = self.decoder.decode(content, structure)
        assert result["main"]["key"] == "value"

    def test_decode_with_sections(self):
        content = """[database]
port=5432
host=localhost"""
        structure = {"format": "key-value"}
        result = self.decoder.decode(content, structure)
        assert result["database"]["port"] == 5432
        assert result["database"]["host"] == "localhost"

    def test_decode_boolean_yes(self):
        content = "enabled=yes"
        structure = {"format": "key-value"}
        result = self.decoder.decode(content, structure)
        assert result["main"]["enabled"] is True

    def test_decode_boolean_true(self):
        content = "enabled=true"
        structure = {"format": "key-value"}
        result = self.decoder.decode(content, structure)
        assert result["main"]["enabled"] is True

    def test_decode_boolean_on(self):
        content = "enabled=on"
        structure = {"format": "key-value"}
        result = self.decoder.decode(content, structure)
        assert result["main"]["enabled"] is True

    def test_decode_boolean_1(self):
        content = "enabled=1"
        structure = {"format": "key-value"}
        result = self.decoder.decode(content, structure)
        assert result["main"]["enabled"] is True

    def test_decode_boolean_no(self):
        content = "disabled=no"
        structure = {"format": "key-value"}
        result = self.decoder.decode(content, structure)
        assert result["main"]["disabled"] is False

    def test_decode_boolean_false(self):
        content = "disabled=false"
        structure = {"format": "key-value"}
        result = self.decoder.decode(content, structure)
        assert result["main"]["disabled"] is False

    def test_decode_boolean_off(self):
        content = "disabled=off"
        structure = {"format": "key-value"}
        result = self.decoder.decode(content, structure)
        assert result["main"]["disabled"] is False

    def test_decode_boolean_0(self):
        content = "disabled=0"
        structure = {"format": "key-value"}
        result = self.decoder.decode(content, structure)
        assert result["main"]["disabled"] is False

    def test_decode_integer(self):
        content = "port=8080"
        structure = {"format": "key-value"}
        result = self.decoder.decode(content, structure)
        assert result["main"]["port"] == 8080

    def test_decode_float(self):
        content = "rate=3.14"
        structure = {"format": "key-value"}
        result = self.decoder.decode(content, structure)
        assert result["main"]["rate"] == "3.14"

    def test_decode_quoted_values(self):
        content = 'message="hello world"'
        structure = {"format": "key-value"}
        result = self.decoder.decode(content, structure)
        assert result["main"]["message"] == "hello world"

    def test_decode_quoted_values_single(self):
        content = "message='hello world'"
        structure = {"format": "key-value"}
        result = self.decoder.decode(content, structure)
        assert result["main"]["message"] == "hello world"

    def test_decode_ignore_comments(self):
        content = """# This is a comment
key=value
; Another comment
another=value"""
        structure = {"format": "key-value"}
        result = self.decoder.decode(content, structure)
        assert result["main"]["key"] == "value"
        assert result["main"]["another"] == "value"

    def test_decode_line_continuation(self):
        content = """key=value1 \\
value2"""
        structure = {"format": "key-value"}
        result = self.decoder.decode(content, structure)
        assert "value1" in result["main"]["key"]
        assert "value2" in result["main"]["key"]

    def test_decode_empty_value(self):
        content = "key="
        structure = {"format": "key-value"}
        result = self.decoder.decode(content, structure)
        assert result["main"]["key"] == ""

    def test_decode_custom_delimiter(self):
        self.decoder.delimiter = ":"
        content = "key:value"
        structure = {"format": "key-value", "syntax": {"delimiter": ":"}}
        result = self.decoder.decode(content, structure)
        assert result["main"]["key"] == "value"

    def test_decode_encode_roundtrip(self):
        original_data = {
            "main": {
                "host": "localhost",
                "port": 8080,
                "enabled": True
            }
        }
        structure = {"format": "key-value"}

        encoded = self.decoder.encode(original_data, structure)
        decoded = self.decoder.decode(encoded, structure)

        assert decoded["main"]["host"] == "localhost"
        assert decoded["main"]["port"] == 8080
        assert decoded["main"]["enabled"] is True

    def test_decode_multiple_sections_roundtrip(self):
        original_data = {
            "main": {"host": "localhost"},
            "database": {"port": 5432, "enabled": True}
        }
        structure = {"format": "key-value"}

        encoded = self.decoder.encode(original_data, structure)
        decoded = self.decoder.decode(encoded, structure)

        assert decoded["main"]["host"] == "localhost"
        assert decoded["database"]["port"] == 5432
        assert decoded["database"]["enabled"] is True

    def test_validate_same_as_encoder(self):
        data = {"main": {"port": 8080}}
        structure = {
            "format": "key-value",
            "structures": {
                "main": {
                    "options": {
                        "port": {"type": "integer", "required": True}
                    }
                }
            }
        }
        errors = self.decoder.validate(data, structure)
        assert len(errors) == 0

    def test_validate_required_missing(self):
        data = {"main": {}}
        structure = {
            "format": "key-value",
            "structures": {
                "main": {
                    "options": {
                        "port": {"type": "integer", "required": True}
                    }
                }
            }
        }
        errors = self.decoder.validate(data, structure)
        assert len(errors) > 0

    def test_validate_unknown_option(self):
        data = {"main": {"unknown": "value"}}
        structure = {
            "format": "key-value",
            "structures": {
                "main": {
                    "options": {}
                }
            }
        }
        errors = self.decoder.validate(data, structure)
        assert len(errors) > 0
