import pytest
import sys
import os
import tempfile
import yaml
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "lib"))

from libregistry import definitions


class TestDefinitionsGetYaml:
    @pytest.fixture
    def temp_def_dir(self, tmp_path):
        return tmp_path

    def test_get_yaml_valid_file(self, temp_def_dir, monkeypatch):
        test_file = temp_def_dir / "test.yaml"
        test_data = {"key": "value", "number": 42}
        with open(test_file, "w") as f:
            yaml.dump(test_data, f)
        
        monkeypatch.setattr(definitions.const, "DIRECTORY_DEFINITION", str(temp_def_dir))
        
        result = definitions.get_yaml("test.yaml")
        assert result == test_data

    def test_get_yaml_file_not_found(self, temp_def_dir, monkeypatch, capsys):
        monkeypatch.setattr(definitions.const, "DIRECTORY_DEFINITION", str(temp_def_dir))
        
        result = definitions.get_yaml("nonexistent.yaml")
        assert result == {}

    def test_get_yaml_nested_dict(self, temp_def_dir, monkeypatch):
        test_file = temp_def_dir / "nested.yaml"
        test_data = {"outer": {"inner": {"value": 42}}}
        with open(test_file, "w") as f:
            yaml.dump(test_data, f)
        
        monkeypatch.setattr(definitions.const, "DIRECTORY_DEFINITION", str(temp_def_dir))
        
        result = definitions.get_yaml("nested.yaml")
        assert result["outer"]["inner"]["value"] == 42


class TestDefinitionsGetMainDefinition:
    @pytest.fixture
    def mock_definitions_dir(self, tmp_path, monkeypatch):
        def mock_get_yaml(path):
            if path == "manifest.yaml":
                return {"categories": ["system_components", "system_applications"]}
            elif path == "system_components/packages.yaml":
                return {"packages": {"docker": {}, "nginx": {}}}
            elif path == "system_applications/packages.yaml":
                return {"packages": {"postfix": {}}}
            return {}
        
        monkeypatch.setattr(definitions, "get_yaml", mock_get_yaml)
        return tmp_path

    def test_get_main_definition_structure(self, mock_definitions_dir):
        result = definitions.get_main_definition()
        
        assert "categories" in result
        assert "packages" in result

    def test_get_main_definition_loads_categories(self, mock_definitions_dir):
        result = definitions.get_main_definition()
        
        assert "system_components" in result["packages"]
        assert "system_applications" in result["packages"]

    def test_get_main_definition_loads_packages(self, mock_definitions_dir):
        result = definitions.get_main_definition()
        
        assert "docker" in result["packages"]["system_components"]
        assert "nginx" in result["packages"]["system_components"]
        assert "postfix" in result["packages"]["system_applications"]


class TestDefinitionsGetPackageDefinition:
    @pytest.fixture
    def mock_definitions_dir(self, tmp_path, monkeypatch):
        def mock_get_yaml(path):
            if path == "system_components/docker/manifest.yaml":
                return {
                    "name": "Docker",
                    "version": "1.0",
                    "detect_installed": ["/usr/bin/docker"]
                }
            elif path == "system_components/nginx/manifest.yaml":
                return {"name": "Nginx"}
            return {}
        
        monkeypatch.setattr(definitions, "get_yaml", mock_get_yaml)
        return tmp_path

    def test_get_package_definition_valid(self, mock_definitions_dir):
        main_def = {"packages": {}}
        
        result = definitions.get_package_definition(main_def, "system_components", "docker")
        
        assert result is not None
        assert result["name"] == "Docker"
        assert result["detect_installed"] == ["/usr/bin/docker"]

    def test_get_package_definition_empty_manifest(self, mock_definitions_dir, monkeypatch, capsys):
        def mock_get_yaml_empty(path):
            if path == "system_components/nginx/manifest.yaml":
                return {}
            return {}
        
        monkeypatch.setattr(definitions, "get_yaml", mock_get_yaml_empty)
        
        main_def = {"packages": {}}
        result = definitions.get_package_definition(main_def, "system_components", "nginx")
        
        assert result is None or result == {}

    def test_get_package_definition_missing(self, mock_definitions_dir, monkeypatch):
        main_def = {"packages": {}}
        
        result = definitions.get_package_definition(main_def, "system_components", "nonexistent")
        
        assert result is None


class TestDefinitionsIntegration:
    def test_full_definition_loading(self, monkeypatch):
        yaml_calls = []
        
        def mock_get_yaml(path):
            yaml_calls.append(path)
            if path == "manifest.yaml":
                return {"categories": ["test_category"]}
            elif path == "test_category/packages.yaml":
                return {"packages": {"test_package": {}}}
            elif path == "test_category/test_package/manifest.yaml":
                return {"name": "Test Package", "version": "1.0"}
            return {}
        
        monkeypatch.setattr(definitions, "get_yaml", mock_get_yaml)
        
        result = definitions.get_main_definition()
        
        assert "packages" in result
        assert len(yaml_calls) > 0

    def test_get_package_with_metadata_only(self, monkeypatch):
        def mock_get_yaml(path):
            if path == "system_components/docker/manifest.yaml":
                return {
                    "name": "Docker",
                    "version": "1.0",
                    "metadata": {"description": "Container runtime"},
                    "detect_installed": ["/usr/bin/docker"]
                }
            return {}
        
        monkeypatch.setattr(definitions, "get_yaml", mock_get_yaml)
        
        main_def = {"packages": {}}
        result = definitions.get_package_definition(main_def, "system_components", "docker", metadata_only=True)
        
        assert result is not None
        assert "metadata" in result or result.get("name") == "Docker"
