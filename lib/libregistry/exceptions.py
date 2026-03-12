"""Custom exceptions for libregistry"""


class RegistryError(Exception):
    """Base exception for all registry errors"""
    pass


class ConfigurationNotFoundError(RegistryError):
    """Raised when a configuration file or path does not exist"""
    pass


class PermissionDeniedError(RegistryError):
    """Raised when insufficient permissions to perform an operation"""
    pass


class ValidationError(RegistryError):
    """Raised when data fails schema validation"""
    def __init__(self, message: str, errors: list = None):
        super().__init__(message)
        self.errors = errors or []


class EncodingError(RegistryError):
    """Raised when encoding data to a file format fails"""
    pass


class DecodingError(RegistryError):
    """Raised when decoding a file fails"""
    pass


class DefinitionError(RegistryError):
    """Raised when there's an issue with a definition"""
    pass


class StructureError(RegistryError):
    """Raised when there's an issue with the configuration structure"""
    pass


class BackupError(RegistryError):
    """Raised when backup operations fail"""
    pass


class DependencyError(RegistryError):
    """Raised when option dependencies are not satisfied"""
    pass
