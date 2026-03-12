from abc import ABC, abstractmethod
from typing import Dict, Any, List


class FileTypeDecoder(ABC):
    """Abstract base class for file type decoders"""

    @abstractmethod
    def decode(self, file_content: str, structure: Dict[str, Any]) -> Dict[str, Any]:
        """Decode file content according to structure definition"""
        pass

    @abstractmethod
    def encode(self, data: Dict[str, Any], structure: Dict[str, Any]) -> str:
        """Encode data back to file content according to structure definition"""
        pass

    @abstractmethod
    def validate(self, data: Dict[str, Any], structure: Dict[str, Any]) -> List[str]:
        """Validate data against structure definition, return list of errors"""
        pass
