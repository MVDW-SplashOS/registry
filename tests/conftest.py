import pytest
import sys
from pathlib import Path

lib_path = str(Path(__file__).parent.parent.parent / "lib")
if lib_path not in sys.path:
    sys.path.insert(0, lib_path)


@pytest.fixture
def project_root():
    return Path(__file__).parent.parent.parent


@pytest.fixture
def lib_path_fixture():
    return Path(__file__).parent.parent.parent / "lib"


@pytest.fixture
def sample_data():
    return {
        "main": {
            "host": "localhost",
            "port": 8080,
            "enabled": True
        }
    }


@pytest.fixture
def sample_nested_data():
    return {
        "server": {
            "database": {
                "host": "db.local",
                "port": 5432,
                "settings": {
                    "timeout": 30,
                    "pool_size": 10
                }
            }
        }
    }


@pytest.fixture
def sample_structure():
    return {
        "format": "json",
        "structures": {
            "main": {
                "options": {
                    "host": {"type": "string"},
                    "port": {"type": "integer", "min": 1, "max": 65535},
                    "enabled": {"type": "boolean"}
                }
            }
        }
    }


@pytest.fixture
def sample_structure_with_required():
    return {
        "format": "json",
        "structures": {
            "main": {
                "options": {
                    "host": {"type": "string", "required": True},
                    "port": {"type": "integer", "required": True},
                    "enabled": {"type": "boolean"}
                }
            }
        }
    }


@pytest.fixture
def empty_data():
    return {}


@pytest.fixture
def list_data():
    return {
        "servers": ["server1", "server2", "server3"],
        "ports": [80, 443, 8080]
    }
