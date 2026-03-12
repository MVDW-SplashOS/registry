import os
import logging
import importlib
from typing import Dict, Any, List, Optional
from .base import FileTypeEncoder

logger = logging.getLogger(__name__)


class Encoder:
    """Main encoder class that handles file type encoding and validation"""

    def __init__(self, filetypes: Optional[Dict[str, FileTypeEncoder]] = None):
        if filetypes is not None:
            self.filetypes = filetypes
        else:
            self.filetypes: Dict[str, FileTypeEncoder] = {}
            self._load_filetypes()

    def _load_filetypes(self):
        """Dynamically load all filetype encoders"""
        filetypes_dir = os.path.join(os.path.dirname(__file__), "filetypes")

        if not os.path.exists(filetypes_dir):
            return

        for item in os.listdir(filetypes_dir):
            item_path = os.path.join(filetypes_dir, item)
            if os.path.isdir(item_path) and not item.startswith("__"):
                try:
                    module_name = f"libregistry.encoder.filetypes.{item}"
                    module = importlib.import_module(module_name)

                    class_name = (
                        f"{item.replace('-', '_').title().replace('_', '')}Encoder"
                    )
                    if hasattr(module, class_name):
                        encoder_class = getattr(module, class_name)
                        encoder_instance = encoder_class()
                        self.filetypes[item] = encoder_instance

                except ImportError as e:
                    logger.warning("Could not load filetype encoder for %s: %s", item, e)

    def get_filetype_encoder(self, filetype: str) -> Optional[FileTypeEncoder]:
        """Get an encoder for the specified filetype"""
        if not filetype:
            return None

        normalized = filetype.replace("_", "-")
        return self.filetypes.get(normalized)

    def encode_data(self, data: Dict[str, Any], structure: Dict[str, Any]) -> str:
        """Encode data using the appropriate filetype encoder"""
        filetype = structure.get("format")
        if not filetype:
            raise ValueError("Filetype not specified in structure")

        encoder = self.get_filetype_encoder(filetype)
        if not encoder:
            raise ValueError(f"No encoder available for filetype: {filetype}")

        # Validate structure before encoding
        validation_errors = encoder.validate_structure(data, structure)
        if validation_errors:
            raise ValueError(f"Data validation failed: {'; '.join(validation_errors)}")

        return encoder.encode(data, structure)

    def supported_filetypes(self) -> List[str]:
        """Get list of supported filetypes"""
        return list(self.filetypes.keys())


_default_encoder: Optional[Encoder] = None


def get_encoder() -> Encoder:
    """Get the global encoder instance (factory method for testability)."""
    global _default_encoder
    if _default_encoder is None:
        _default_encoder = Encoder()
    return _default_encoder


def set_encoder(encoder_instance: Encoder) -> None:
    """Set a custom encoder instance (useful for testing)."""
    global _default_encoder
    _default_encoder = encoder_instance


def reset_encoder() -> None:
    """Reset the encoder to create a new instance on next get_encoder() call."""
    global _default_encoder
    _default_encoder = None


class _DefaultEncoderProxy:
    """Proxy to maintain backward compatibility with global encoder usage."""
    def __getattr__(self, name: str):
        return getattr(get_encoder(), name)


encoder = _DefaultEncoderProxy()
