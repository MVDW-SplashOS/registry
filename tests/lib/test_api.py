import pytest
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "lib"))

from libregistry.api import RegistrySession


class TestRegistrySession:
    @pytest.fixture
    def mock_definitions(self, monkeypatch):
        mock_main_def = {
            "categories": ["system_components", "system_applications"],
            "packages": {
                "system_components": ["docker", "nginx"],
                "system_applications": ["postfix"]
            }
        }
        mock_pkg_def_docker = {
            "name": "Docker",
            "detect_installed": ["/usr/bin/docker", "/var/run/docker.sock"]
        }
        mock_pkg_def_nginx = {
            "name": "Nginx",
            "detect_installed": ["/usr/sbin/nginx"]
        }
        
        def mock_get_package_definition(main_def, category, package, metadata_only=False):
            if category == "system_components":
                if package == "docker":
                    return mock_pkg_def_docker
                elif package == "nginx":
                    return mock_pkg_def_nginx
            return None
        
        monkeypatch.setattr("libregistry.definitions.get_main_definition", lambda: mock_main_def)
        monkeypatch.setattr("libregistry.definitions.get_package_definition", mock_get_package_definition)

    def test_registry_session_init(self, mock_definitions):
        session = RegistrySession()
        
        assert session.main_definition is not None
        assert "packages" in session.main_definition

    def test_check_packages_installed_all_exist(self, mock_definitions):
        with patch("os.path.exists", return_value=True):
            session = RegistrySession()
            result = session.check_packages_installed()
            
            assert "system_components" in result
            assert "docker" in result["system_components"]
            assert "nginx" in result["system_components"]

    def test_check_packages_installed_some_missing(self, mock_definitions):
        def mock_exists(path):
            return "/docker" in path
        
        with patch("os.path.exists", mock_exists):
            session = RegistrySession()
            result = session.check_packages_installed()
            
            assert "docker" in result["system_components"]
            assert "nginx" not in result["system_components"]

    def test_check_packages_installed_none_exist(self, mock_definitions):
        with patch("os.path.exists", return_value=False):
            session = RegistrySession()
            result = session.check_packages_installed()
            
            assert "system_components" in result
            assert "docker" not in result["system_components"]
            assert "nginx" not in result["system_components"]

    def test_check_packages_installed_returns_modified_def(self, mock_definitions):
        with patch("os.path.exists", return_value=True):
            session = RegistrySession()
            result = session.check_packages_installed()
            
            assert result is session.main_definition["packages"]

    def test_categories_populated(self, mock_definitions):
        session = RegistrySession()
        
        assert hasattr(session, 'categories')
        assert session.categories == {}


class TestRegistrySessionEdgeCases:
    def test_session_with_empty_packages(self, monkeypatch):
        mock_main_def = {
            "categories": [],
            "packages": {}
        }
        
        monkeypatch.setattr("libregistry.definitions.get_main_definition", lambda: mock_main_def)
        
        session = RegistrySession()
        result = session.check_packages_installed()
        
        assert result == {}

    def test_session_with_no_detect_paths(self, monkeypatch):
        mock_main_def = {
            "categories": ["test_category"],
            "packages": {
                "test_category": ["test_package"]
            }
        }
        
        def mock_get_package_definition(main_def, category, package, metadata_only=False):
            return {"name": "Test Package", "detect_installed": []}
        
        monkeypatch.setattr("libregistry.definitions.get_main_definition", lambda: mock_main_def)
        monkeypatch.setattr("libregistry.definitions.get_package_definition", mock_get_package_definition)
        
        session = RegistrySession()
        result = session.check_packages_installed()
        
        assert "test_package" not in result["test_category"]
