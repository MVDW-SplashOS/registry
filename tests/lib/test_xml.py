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

    def test_encode_float(self):
        data = {"rate": 3.14}
        structure = {"format": "xml", "root_element": "config"}
        result = self.encoder.encode(data, structure)
        assert "<rate>3.14</rate>" in result

    def test_encode_list(self):
        data = {"servers": ["server1", "server2"]}
        structure = {"format": "xml", "root_element": "config"}
        result = self.encoder.encode(data, structure)
        assert "<servers>" in result

    def test_encode_empty_dict(self):
        data = {}
        structure = {"format": "xml", "root_element": "config"}
        result = self.encoder.encode(data, structure)
        assert result

    def test_encode_unicode(self):
        data = {"message": "hello world"}
        structure = {"format": "xml", "root_element": "config"}
        result = self.encoder.encode(data, structure)
        assert "hello world" in result

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

    def test_validate_structure_invalid_type(self):
        data = {"main": {"port": "not_an_integer"}}
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
        assert len(errors) > 0

    def test_encode_decode_roundtrip(self):
        decoder = XmlDecoder()
        original_data = {
            "server": {
                "host": "localhost",
                "port": "8080",
                "enabled": "true"
            }
        }
        structure = {"format": "xml", "root_element": "config"}

        encoded = self.encoder.encode(original_data, structure)
        decoded = decoder.decode(encoded, structure)

        assert decoded["server"]["host"] == "localhost"


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

    def test_decode_list(self):
        content = "<config><servers><server>server1</server><server>server2</server></servers></config>"
        structure = {"format": "xml"}
        result = self.decoder.decode(content, structure)
        assert "servers" in result

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

    def test_decode_empty_xml(self):
        content = "<config></config>"
        structure = {"format": "xml"}
        result = self.decoder.decode(content, structure)
        assert result == {}

    def test_decode_attributes(self):
        content = '<config key="value"></config>'
        structure = {"format": "xml"}
        result = self.decoder.decode(content, structure)
        assert "@attributes" in result or "key" in result.get("config", {})
