import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "lib"))

from libregistry.encoder.filetypes.xml.encoder import XmlEncoder
from libregistry.decoder.filetypes.xml.decoder import XmlDecoder


class TestXmlEncoder:
    def setup_method(self):
        self.encoder = XmlEncoder()

    def test_encode_simple_dict(self):
        data = {"key": "value"}
        structure = {"format": "xml", "root_element": "config"}
        result = self.encoder.encode(data, structure)
        assert "<key>value</key>" in result

    def test_encode_nested_dict(self):
        data = {"section": {"key": "value"}}
        structure = {"format": "xml", "root_element": "config"}
        result = self.encoder.encode(data, structure)
        assert "<section>" in result
        assert "<key>value</key>" in result

    def test_encode_boolean(self):
        data = {"enabled": True, "disabled": False}
        structure = {"format": "xml", "root_element": "config"}
        result = self.encoder.encode(data, structure)
        assert "<enabled>True</enabled>" in result
        assert "<disabled>False</disabled>" in result

    def test_encode_integer(self):
        data = {"port": 8080}
        structure = {"format": "xml", "root_element": "config"}
        result = self.encoder.encode(data, structure)
        assert "<port>8080</port>" in result

    def test_validate_structure_valid(self):
        data = {"main": {"port": 8080}}
        structure = {
            "format": "xml",
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


class TestXmlDecoder:
    def setup_method(self):
        self.decoder = XmlDecoder()

    def test_decode_simple_key_value(self):
        content = "<config><key>value</key></config>"
        structure = {"format": "xml"}
        result = self.decoder.decode(content, structure)
        assert result["key"] == "value"

    def test_decode_nested(self):
        content = "<config><section><key>value</key></section></config>"
        structure = {"format": "xml"}
        result = self.decoder.decode(content, structure)
        assert result["section"]["key"] == "value"

    def test_decode_encode_roundtrip(self):
        original_data = {"server": {"host": "localhost", "port": "8080"}}
        structure = {"format": "xml", "root_element": "config"}
        
        encoded = self.decoder.encode(original_data, structure)
        decoded = self.decoder.decode(encoded, structure)
        
        assert decoded["server"]["host"] == "localhost"

    def test_decode_invalid_xml(self):
        content = "<invalid>xml[[["
        structure = {"format": "xml"}
        with pytest.raises(ValueError):
            self.decoder.decode(content, structure)
