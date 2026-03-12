import os
import logging
import importlib
from typing import Dict, Any, List, Optional
from .base import FileTypeDecoder
from .file import File
from ..encoder import encoder as encoder_module

logger = logging.getLogger(__name__)


class Decoder:
    """Main decoder class that handles file type detection and decoding"""

    def __init__(self, filetypes: Optional[Dict[str, FileTypeDecoder]] = None):
        if filetypes is not None:
            self.filetypes = filetypes
        else:
            self.filetypes: Dict[str, FileTypeDecoder] = {}
            self._load_filetypes()

    def _load_filetypes(self):
        """Dynamically load all filetype decoders from the filetypes directory"""
        filetypes_dir = os.path.join(os.path.dirname(__file__), "filetypes")

        for item in os.listdir(filetypes_dir):
            item_path = os.path.join(filetypes_dir, item)
            if os.path.isdir(item_path) and not item.startswith("__"):
                try:
                    # Import the filetype module
                    module_name = f"libregistry.decoder.filetypes.{item}"
                    module = importlib.import_module(module_name)

                    # Look for a class named after the filetype (e.g., KeyValueDecoder)
                    class_name = (
                        f"{item.replace('-', '_').title().replace('_', '')}Decoder"
                    )
                    if hasattr(module, class_name):
                        decoder_class = getattr(module, class_name)
                        decoder_instance = decoder_class()
                        self.filetypes[item] = decoder_instance

                except ImportError as e:
                    logger.warning(
                        "Could not load filetype decoder for %s: %s", item, e
                    )

    def get_filetype_decoder(self, filetype: str) -> Optional[FileTypeDecoder]:
        """Get a decoder for the specified filetype"""
        if not filetype:
            return None

        normalized = filetype.replace("_", "-")
        return self.filetypes.get(normalized)

    def decode_file(self, file_path: str, structure: Dict[str, Any]) -> Dict[str, Any]:
        """Decode a file using its structure definition"""
        file = File(file_path)
        file_content = file.read()

        # Get filetype from structure or detect from file extension
        filetype = structure.get("format")
        if not filetype:
            filetype = self._detect_filetype(file_path)

        decoder = self.get_filetype_decoder(filetype)
        if not decoder:
            raise ValueError(f"No decoder available for filetype: {filetype}")

        return decoder.decode(file_content, structure)

    def encode_file(
        self, data: Dict[str, Any], structure: Dict[str, Any], file_path: str
    ) -> None:
        """Encode data and write to file using structure definition"""
        filetype = structure.get("format")
        if not filetype:
            filetype = self._detect_filetype(file_path)

        enc = encoder_module.get_encoder().get_filetype_encoder(filetype)
        if not enc:
            raise ValueError(f"No encoder available for filetype: {filetype}")

        file_content = enc.encode(data, structure)

        file = File(file_path)
        file.write(file_content)

    def validate_file(self, file_path: str, structure: Dict[str, Any]) -> List[str]:
        """Validate a file against its structure definition"""
        data = self.decode_file(file_path, structure)
        filetype = structure.get("format")

        decoder = self.get_filetype_decoder(filetype)
        if not decoder:
            return [f"No decoder available for filetype: {filetype}"]

        return decoder.validate(data, structure)

    def _detect_filetype(self, file_path: str) -> str:
        """Detect filetype from file extension"""
        ext = os.path.splitext(file_path)[1].lower()

        filetype_map = {
            ".conf": "key-value",
            ".cfg": "key-value",
            ".ini": "ini",
            ".json": "json",
            ".xml": "xml",
            ".yaml": "yaml",
            ".yml": "yaml",
            ".toml": "toml",
        }

        return filetype_map.get(ext, "key-value")


_default_decoder: Optional[Decoder] = None


def get_decoder() -> Decoder:
    """Get the global decoder instance (factory method for testability)."""
    global _default_decoder
    if _default_decoder is None:
        _default_decoder = Decoder()
    return _default_decoder


def set_decoder(decoder_instance: Decoder) -> None:
    """Set a custom decoder instance (useful for testing)."""
    global _default_decoder
    _default_decoder = decoder_instance


def reset_decoder() -> None:
    """Reset the decoder to create a new instance on next get_decoder() call."""
    global _default_decoder
    _default_decoder = None


class _DefaultDecoderProxy:
    """Proxy to maintain backward compatibility with global decoder usage."""

    def __getattr__(self, name: str):
        return getattr(get_decoder(), name)


decoder = _DefaultDecoderProxy()
