import pytest
import sys
import tempfile
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "lib"))

from libregistry.encoder.filetypes.ini.encoder import IniEncoder
from libregistry.decoder.filetypes.ini.decoder import IniDecoder
from libregistry.exceptions import EncodingError, DecodingError


class TestIniEncoder:
    def setup_method(self):
        self.encoder = IniEncoder()

    def test_encode_simple_dict(self):
        data = {"main": {"key": "value"}}
        structure = {"format": "ini"}
        result = self.encoder.encode(data, structure)
        assert "key = value" in result

    def test_encode_sections(self):
        data = {
            "section1": {"key1": "value1"},
            "section2": {"key2": "value2"}
        }
        structure = {"format": "ini"}
        result = self.encoder.encode(data, structure)
        assert "[section1]" in result
        assert "[section2]" in result

    def test_encode_boolean(self):
        data = {"main": {"enabled": True, "disabled": False}}
        structure = {"format": "ini"}
        result = self.encoder.encode(data, structure)
        assert "enabled = yes" in result
        assert "disabled = no" in result

    def test_encode_integer(self):
        data = {"main": {"port": 8080}}
        structure = {"format": "ini"}
        result = self.encoder.encode(data, structure)
        assert "port = 8080" in result

    def test_encode_list(self):
        data = {"main": {"servers": ["server1", "server2"]}}
        structure = {"format": "ini"}
        result = self.encoder.encode(data, structure)
        assert "server1" in result
        assert "server2" in result

    def test_validate_structure_valid(self):
        data = {"main": {"port": 8080}}
        structure = {
            "format": "ini",
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
            "format": "ini",
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


class TestIniDecoder:
    def setup_method(self):
        self.decoder = IniDecoder()

    def test_decode_simple_key_value(self):
        content = """[main]
key = value
"""
        structure = {"format": "ini"}
        result = self.decoder.decode(content, structure)
        assert result["main"]["key"] == "value"

    def test_decode_sections(self):
        content = """[section1]
key1 = value1

[section2]
key2 = value2
"""
        structure = {"format": "ini"}
        result = self.decoder.decode(content, structure)
        assert "section1" in result
        assert "section2" in result
        assert result["section1"]["key1"] == "value1"
        assert result["section2"]["key2"] == "value2"

    def test_decode_boolean(self):
        content = """[main]
enabled = yes
disabled = no
"""
        structure = {"format": "ini"}
        result = self.decoder.decode(content, structure)
        assert result["main"]["enabled"] == "yes"
        assert result["main"]["disabled"] == "no"

    def test_decode_integer(self):
        content = """[main]
port = 8080
"""
        structure = {"format": "ini"}
        result = self.decoder.decode(content, structure)
        assert result["main"]["port"] == "8080"

    def test_decode_comments(self):
        content = """[main]
# This is a comment
key = value
; Another comment
key2 = value2
"""
        structure = {"format": "ini"}
        result = self.decoder.decode(content, structure)
        assert result["main"]["key"] == "value"
        assert result["main"]["key2"] == "value2"

    def test_decode_encode_roundtrip(self):
        original_data = {
            "main": {
                "host": "localhost",
                "port": "8080"
            },
            "database": {
                "host": "db.local",
                "port": "5432"
            }
        }
        structure = {"format": "ini"}
        
        encoded = self.decoder.encode(original_data, structure)
        decoded = self.decoder.decode(encoded, structure)
        
        assert decoded["main"]["host"] == "localhost"
        assert decoded["database"]["host"] == "db.local"

    def test_validate_valid_data(self):
        data = {"main": {"port": 8080}}
        structure = {
            "format": "ini",
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
            "format": "ini",
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

    def test_validate_required_option_missing(self):
        data = {"main": {}}
        structure = {
            "format": "ini",
            "structures": {
                "main": {
                    "options": {
                        "port": {"type": "integer", "required": True}
                    }
                }
            }
        }
        errors = self.decoder.validate(data, structure)
        assert any("required" in err.lower() for err in errors)
