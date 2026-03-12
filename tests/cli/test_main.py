import pytest
import sys
import tempfile
import os
import yaml
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "lib"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "cli"))

from registry.main import RegistryCLI


class TestCLISetCommand:
    @pytest.fixture
    def cli(self, tmp_path):
        with patch.object(RegistryCLI, '_ensure_directories'):
            cli = RegistryCLI(verbose=False)
            cli.changes_file = tmp_path / "changes.yaml"
            cli.backup_dir = tmp_path / "backups"
            cli.backup_dir.mkdir(parents=True, exist_ok=True)
            return cli

    def test_set_simple_value(self, cli, tmp_path):
        cli.set_command("test/category/test_config/key", "value")
        
        with open(cli.changes_file) as f:
            changes = yaml.safe_load(f)
        
        assert changes["test"]["category"]["test_config/key"] == "value"

    def test_set_boolean_true(self, cli):
        cli.set_command("test/category/test_config/enabled", "true")
        
        with open(cli.changes_file) as f:
            changes = yaml.safe_load(f)
        
        assert changes["test"]["category"]["test_config/enabled"] is True

    def test_set_boolean_yes(self, cli):
        cli.set_command("test/category/test_config/enabled", "yes")
        
        with open(cli.changes_file) as f:
            changes = yaml.safe_load(f)
        
        assert changes["test"]["category"]["test_config/enabled"] is True

    def test_set_boolean_false(self, cli):
        cli.set_command("test/category/test_config/enabled", "false")
        
        with open(cli.changes_file) as f:
            changes = yaml.safe_load(f)
        
        assert changes["test"]["category"]["test_config/enabled"] is False

    def test_set_integer(self, cli):
        cli.set_command("test/category/test_config/port", "8080")
        
        with open(cli.changes_file) as f:
            changes = yaml.safe_load(f)
        
        assert changes["test"]["category"]["test_config/port"] == 8080

    def test_set_float(self, cli):
        cli.set_command("test/category/test_config/rate", "3.14")
        
        with open(cli.changes_file) as f:
            changes = yaml.safe_load(f)
        
        assert changes["test"]["category"]["test_config/rate"] == 3.14

    def test_set_string_with_spaces(self, cli):
        cli.set_command("test/category/test_config/name", "hello world")
        
        with open(cli.changes_file) as f:
            changes = yaml.safe_load(f)
        
        assert changes["test"]["category"]["test_config/name"] == "hello world"


class TestCLIViewChanges:
    @pytest.fixture
    def cli(self, tmp_path):
        with patch.object(RegistryCLI, '_ensure_directories'):
            cli = RegistryCLI(verbose=False)
            cli.changes_file = tmp_path / "changes.yaml"
            cli.backup_dir = tmp_path / "backups"
            cli.backup_dir.mkdir(parents=True, exist_ok=True)
            return cli

    def test_view_changes_empty(self, cli, capsys):
        cli.view_changes_command()
        captured = capsys.readouterr()
        assert "No pending changes" in captured.out

    def test_view_changes_with_data(self, cli, capsys):
        changes = {
            "test": {
                "category": {
                    "config/key": "value"
                }
            }
        }
        with open(cli.changes_file, 'w') as f:
            yaml.dump(changes, f)
        
        cli.view_changes_command()
        
        captured = capsys.readouterr()
        assert "test:" in captured.out
        assert "config/key = value" in captured.out


class TestCLIDiscard:
    @pytest.fixture
    def cli(self, tmp_path):
        with patch.object(RegistryCLI, '_ensure_directories'):
            cli = RegistryCLI(verbose=False)
            cli.changes_file = tmp_path / "changes.yaml"
            cli.backup_dir = tmp_path / "backups"
            cli.backup_dir.mkdir(parents=True, exist_ok=True)
            return cli

    def test_discard_empty(self, cli, capsys):
        cli.discard_command()
        captured = capsys.readouterr()
        assert "No changes to discard" in captured.out

    def test_discard_with_changes(self, cli):
        changes = {"test": {"category": {"key": "value"}}}
        with open(cli.changes_file, 'w') as f:
            yaml.dump(changes, f)
        
        cli.discard_command()
        
        with open(cli.changes_file) as f:
            remaining = yaml.safe_load(f)
        
        assert remaining == {} or remaining is None


class TestCLIReset:
    @pytest.fixture
    def cli(self, tmp_path):
        with patch.object(RegistryCLI, '_ensure_directories'):
            cli = RegistryCLI(verbose=False)
            cli.changes_file = tmp_path / "changes.yaml"
            cli.backup_dir = tmp_path / "backups"
            cli.backup_dir.mkdir(parents=True, exist_ok=True)
            return cli

    def test_reset_existing_path(self, cli):
        changes = {
            "test": {
                "category": {
                    "config/key": "value"
                }
            }
        }
        with open(cli.changes_file, 'w') as f:
            yaml.dump(changes, f)
        
        cli.reset_command("test/category/config/key")
        
        with open(cli.changes_file) as f:
            remaining = yaml.safe_load(f)
        
        assert "config/key" not in remaining.get("test", {}).get("category", {})

    def test_reset_nonexistent_path(self, cli, capsys):
        changes = {"test": {"category": {"key": "value"}}}
        with open(cli.changes_file, 'w') as f:
            yaml.dump(changes, f)
        
        cli.reset_command("test/category/config/other")
        
        captured = capsys.readouterr()
        assert "No pending changes" in captured.out


class TestCLIPathParsing:
    @pytest.fixture
    def cli(self, tmp_path):
        with patch.object(RegistryCLI, '_ensure_directories'):
            cli = RegistryCLI(verbose=False)
            cli.changes_file = tmp_path / "changes.yaml"
            cli.backup_dir = tmp_path / "backups"
            cli.backup_dir.mkdir(parents=True, exist_ok=True)
            return cli

    def test_parse_valid_path(self, cli):
        category, package, config_path = cli._parse_path("category/package/config/key")
        assert category == "category"
        assert package == "package"
        assert config_path == "config/key"

    def test_parse_path_too_short(self, cli):
        with pytest.raises(ValueError) as exc_info:
            cli._parse_path("category/package")
        assert "Invalid path format" in str(exc_info.value)


class TestCLIValidate:
    @pytest.fixture
    def cli(self, tmp_path):
        with patch.object(RegistryCLI, '_ensure_directories'):
            cli = RegistryCLI(verbose=False)
            cli.changes_file = tmp_path / "changes.yaml"
            cli.backup_dir = tmp_path / "backups"
            cli.backup_dir.mkdir(parents=True, exist_ok=True)
            return cli

    def test_validate_empty_changes(self, cli, capsys):
        cli.validate_command()
        captured = capsys.readouterr()
        assert "No pending changes" in captured.out
