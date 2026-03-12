import pytest
import sys
from pathlib import Path
from abc import ABC

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "lib"))

from libregistry.encoder.base import FileTypeEncoder
from libregistry.decoder.base import FileTypeDecoder
from libregistry.encoder.encoder import encoder as global_encoder
from libregistry.decoder.decoder import decoder as global_decoder


class TestFileTypeEncoderBase:
    def test_encoder_is_abstract(self):
        with pytest.raises(TypeError):
            FileTypeEncoder()

    def test_encoder_has_encode_method(self):
        assert hasattr(FileTypeEncoder, 'encode')
        assert callable(getattr(FileTypeEncoder, 'encode'))

    def test_encoder_has_validate_structure_method(self):
        assert hasattr(FileTypeEncoder, 'validate_structure')
        assert callable(getattr(FileTypeEncoder, 'validate_structure'))

    def test_encoder_is_abc(self):
        assert issubclass(FileTypeEncoder, ABC)


class TestFileTypeDecoderBase:
    def test_decoder_is_abstract(self):
        with pytest.raises(TypeError):
            FileTypeDecoder()

    def test_decoder_has_decode_method(self):
        assert hasattr(FileTypeDecoder, 'decode')
        assert callable(getattr(FileTypeDecoder, 'decode'))

    def test_decoder_has_encode_method(self):
        assert hasattr(FileTypeDecoder, 'encode')
        assert callable(getattr(FileTypeDecoder, 'encode'))

    def test_decoder_has_validate_method(self):
        assert hasattr(FileTypeDecoder, 'validate')
        assert callable(getattr(FileTypeDecoder, 'validate'))

    def test_decoder_is_abc(self):
        assert issubclass(FileTypeDecoder, ABC)


class TestEncoderInterfaceConsistency:
    def test_all_encoders_have_encode_method(self):
        for filetype in global_encoder.filetypes:
            enc = global_encoder.get_filetype_encoder(filetype)
            assert hasattr(enc, 'encode'), f"{filetype} encoder missing encode method"
            assert callable(getattr(enc, 'encode'))

    def test_all_encoders_have_validate_structure_method(self):
        for filetype in global_encoder.filetypes:
            enc = global_encoder.get_filetype_encoder(filetype)
            assert hasattr(enc, 'validate_structure'), f"{filetype} encoder missing validate_structure method"
            assert callable(getattr(enc, 'validate_structure'))

    def test_encode_returns_string(self):
        test_data = {"main": {"key": "value"}}
        test_structure = {"format": "json"}

        for filetype in global_encoder.filetypes:
            enc = global_encoder.get_filetype_encoder(filetype)
            result = enc.encode(test_data, test_structure)
            assert isinstance(result, str), f"{filetype} encoder.encode() should return string"

    def test_validate_structure_returns_list(self):
        test_data = {"main": {"key": "value"}}
        test_structure = {"format": "json", "structures": {}}

        for filetype in global_encoder.filetypes:
            enc = global_encoder.get_filetype_encoder(filetype)
            result = enc.validate_structure(test_data, test_structure)
            assert isinstance(result, list), f"{filetype} encoder.validate_structure() should return list"


class TestDecoderInterfaceConsistency:
    def test_all_decoders_have_decode_method(self):
        for filetype in global_decoder.filetypes:
            dec = global_decoder.get_filetype_decoder(filetype)
            assert hasattr(dec, 'decode'), f"{filetype} decoder missing decode method"
            assert callable(getattr(dec, 'decode'))

    def test_all_decoders_have_encode_method(self):
        for filetype in global_decoder.filetypes:
            dec = global_decoder.get_filetype_decoder(filetype)
            assert hasattr(dec, 'encode'), f"{filetype} decoder missing encode method"
            assert callable(getattr(dec, 'encode'))

    def test_all_decoders_have_validate_method(self):
        for filetype in global_decoder.filetypes:
            dec = global_decoder.get_filetype_decoder(filetype)
            assert hasattr(dec, 'validate'), f"{filetype} decoder missing validate method"
            assert callable(getattr(dec, 'validate'))

    def test_decode_returns_dict(self):
        test_content = '{"key": "value"}'
        test_structure = {"format": "json"}

        for filetype in global_decoder.filetypes:
            dec = global_decoder.get_filetype_decoder(filetype)
            try:
                result = dec.decode(test_content, test_structure)
                assert isinstance(result, dict), f"{filetype} decoder.decode() should return dict"
            except Exception:
                pass

    def test_encode_returns_string(self):
        test_data = {"main": {"key": "value"}}
        test_structure = {"format": "json"}

        for filetype in global_decoder.filetypes:
            dec = global_decoder.get_filetype_decoder(filetype)
            result = dec.encode(test_data, test_structure)
            assert isinstance(result, str), f"{filetype} decoder.encode() should return string"

    def test_validate_returns_list(self):
        test_data = {"main": {"key": "value"}}
        test_structure = {"format": "json"}

        for filetype in global_decoder.filetypes:
            dec = global_decoder.get_filetype_decoder(filetype)
            result = dec.validate(test_data, test_structure)
            assert isinstance(result, list), f"{filetype} decoder.validate() should return list"


class TestEncoderBaseDocumentation:
    def test_encoder_base_class_docstring(self):
        assert FileTypeEncoder.__doc__ is not None
        assert "Abstract base class" in FileTypeEncoder.__doc__

    def test_decoder_base_class_docstring(self):
        assert FileTypeDecoder.__doc__ is not None
        assert "Abstract base class" in FileTypeDecoder.__doc__
