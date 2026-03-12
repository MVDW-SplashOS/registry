import pytest
import sys
import tempfile
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "lib"))

from libregistry.encoder.filetypes.toml.encoder import TomlEncoder
from libregistry.decoder.filetypes.toml.decoder import TomlDecoder
from libregistry.exceptions import EncodingError, DecodingError


class TestTomlEncoder:
    def setup_method(self):
        self.encoder = TomlEncoder()

    def test_encode_simple_dict(self):
        data = {"key": "value"}
        structure = {"format": "toml"}
        result = self.encoder.encode(data, structure)
        assert "key" in result
        assert "value" in result

    def test_encode_nested_dict(self):
        data = {"section": {"key": "value"}}
        structure = {"format": "toml"}
        result = self.encoder.encode(data, structure)
        assert "[section]" in result

    def test_encode_boolean(self):
        data = {"enabled": True, "disabled": False}
        structure = {"format": "toml"}
        result = self.encoder.encode(data, structure)
        assert "enabled = true" in result
        assert "disabled = false" in result

    def test_encode_integer(self):
        data = {"port": 8080}
        structure = {"format": "toml"}
        result = self.encoder.encode(data, structure)
        assert "port = 8080" in result

    def test_encode_list(self):
        data = {"servers": ["server1", "server2"]}
        structure = {"format": "toml"}
        result = self.encoder.encode(data, structure)
        assert "server1" in result
        assert "server2" in result

    def test_validate_structure_valid(self):
        data = {"main": {"port": 8080}}
        structure = {
            "format": "toml",
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
            "format": "toml",
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


class TestTomlDecoder:
    def setup_method(self):
        self.decoder = TomlDecoder()

    def test_decode_simple_key_value(self):
        content = 'key = "value"'
        structure = {"format": "toml"}
        result = self.decoder.decode(content, structure)
        assert result["key"] == "value"

    def test_decode_section(self):
        content = """[section]
key = "value"
"""
        structure = {"format": "toml"}
        result = self.decoder.decode(content, structure)
        assert "section" in result
        assert result["section"]["key"] == "value"

    def test_decode_boolean(self):
        content = """enabled = true
disabled = false
"""
        structure = {"format": "toml"}
        result = self.decoder.decode(content, structure)
        assert result["enabled"] is True
        assert result["disabled"] is False

    def test_decode_integer(self):
        content = "port = 8080"
        structure = {"format": "toml"}
        result = self.decoder.decode(content, structure)
        assert result["port"] == 8080

    def test_decode_list(self):
        content = 'servers = ["server1", "server2"]'
        structure = {"format": "toml"}
        result = self.decoder.decode(content, structure)
        assert result["servers"] == ["server1", "server2"]

    def test_decode_encode_roundtrip(self):
        original_data = {
            "server": {
                "host": "localhost",
                "port": 8080,
                "enabled": True
            }
        }
        structure = {"format": "toml"}
        
        encoded = self.decoder.encode(original_data, structure)
        decoded = self.decoder.decode(encoded, structure)
        
        assert decoded["server"]["host"] == "localhost"
        assert decoded["server"]["port"] == 8080

    def test_decode_invalid_toml(self):
        content = "invalid toml [[["
        structure = {"format": "toml"}
        with pytest.raises(DecodingError):
            self.decoder.decode(content, structure)

    def test_validate_valid_data(self):
        data = {"main": {"port": 8080}}
        structure = {
            "format": "toml",
            "structures": {
                "main": {
                    "options": {
                        "port": {"type": "integer"}
                    }
                }
            }
        }
        errors = self.decoder.validate(data, structure)
        assert len(errors) == 0

    def test_validate_invalid_type(self):
        data = {"main": {"port": "not_an_integer"}}
        structure = {
            "format": "toml",
            "structures": {
                "main": {
                    "options": {
                        "port": {"type": "integer"}
                    }
                }
            }
        }
        errors = self.decoder.validate(data, structure)
        assert len(errors) > 0
