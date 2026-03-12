from abc import ABC, abstractmethod
from typing import Dict, Any, List


class FileTypeEncoder(ABC):
    """Abstract base class for file type encoders"""

    @abstractmethod
    def encode(self, data: Dict[str, Any], structure: Dict[str, Any]) -> str:
        """Encode data to file content according to structure definition"""
        pass

    @abstractmethod
    def validate_structure(
        self, data: Dict[str, Any], structure: Dict[str, Any]
    ) -> List[str]:
        """Validate data structure before encoding"""
        pass
