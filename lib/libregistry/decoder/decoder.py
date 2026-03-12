import os
import importlib
from typing import Dict, Any, List, Optional
from .base import FileTypeDecoder
from .file import File


class Decoder:
    """Main decoder class that handles file type detection and decoding"""

    def __init__(self):
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
                    print(f"Warning: Could not load filetype decoder for {item}: {e}")

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

        decoder = self.get_filetype_decoder(filetype)
        if not decoder:
            raise ValueError(f"No encoder available for filetype: {filetype}")

        file_content = decoder.encode(data, structure)

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


# Global decoder instance
decoder = Decoder()
