import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "lib"))

from libregistry.exceptions import (
    RegistryError,
    ConfigurationNotFoundError,
    PermissionDeniedError,
    ValidationError,
    EncodingError,
    DecodingError,
    DefinitionError,
    StructureError,
    BackupError,
    DependencyError,
)


class TestExceptions:
    def test_registry_error(self):
        with pytest.raises(RegistryError):
            raise RegistryError("test error")

    def test_configuration_not_found_error(self):
        with pytest.raises(ConfigurationNotFoundError):
            raise ConfigurationNotFoundError("/etc/config.conf")

    def test_permission_denied_error(self):
        with pytest.raises(PermissionDeniedError):
            raise PermissionDeniedError("Cannot write to /etc/config")

    def test_validation_error(self):
        with pytest.raises(ValidationError) as exc_info:
            raise ValidationError("Validation failed", errors=["error1", "error2"])
        assert exc_info.value.errors == ["error1", "error2"]

    def test_encoding_error(self):
        with pytest.raises(EncodingError):
            raise EncodingError("Failed to encode")

    def test_decoding_error(self):
        with pytest.raises(DecodingError):
            raise DecodingError("Failed to decode")

    def test_definition_error(self):
        with pytest.raises(DefinitionError):
            raise DefinitionError("Invalid definition")

    def test_structure_error(self):
        with pytest.raises(StructureError):
            raise StructureError("Invalid structure")

    def test_backup_error(self):
        with pytest.raises(BackupError):
            raise BackupError("Backup failed")

    def test_dependency_error(self):
        with pytest.raises(DependencyError):
            raise DependencyError("Dependency not satisfied")

    def test_exception_inheritance(self):
        assert issubclass(ConfigurationNotFoundError, RegistryError)
        assert issubclass(PermissionDeniedError, RegistryError)
        assert issubclass(ValidationError, RegistryError)
        assert issubclass(EncodingError, RegistryError)
        assert issubclass(DecodingError, RegistryError)
        assert issubclass(DefinitionError, RegistryError)
        assert issubclass(StructureError, RegistryError)
        assert issubclass(BackupError, RegistryError)
        assert issubclass(DependencyError, RegistryError)
