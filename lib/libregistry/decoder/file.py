import os
import stat
import shutil
from typing import Optional
from .. import logger


class File:
    """File operations class with permission handling"""

    def __init__(self, path: str):
        self.path = path
        self.encoding = "utf-8"

    def read(self) -> str:
        """Read file content with proper encoding handling"""
        try:
            with open(self.path, "r", encoding=self.encoding) as file:
                return file.read()
        except UnicodeDecodeError:
            # Try with different encodings
            for encoding in ["utf-8", "latin-1", "cp1252"]:
                try:
                    with open(self.path, "r", encoding=encoding) as file:
                        return file.read()
                except UnicodeDecodeError:
                    continue
            raise ValueError(
                f"Could not decode file {self.path} with any supported encoding"
            )
        except FileNotFoundError:
            logger.print_error(f"File not found: {self.path}")
            raise
        except PermissionError:
            logger.print_error(f"Permission denied reading file: {self.path}")
            raise
        except Exception as e:
            logger.print_error(f"Error reading file {self.path}: {e}")
            raise

    def write(self, content: str, create_dirs: bool = True) -> None:
        """Write content to file, creating directories if needed"""
        try:
            if create_dirs:
                os.makedirs(os.path.dirname(self.path), exist_ok=True)

            with open(self.path, "w", encoding=self.encoding) as file:
                file.write(content)
        except PermissionError:
            logger.print_error(f"Permission denied writing file: {self.path}")
            raise
        except Exception as e:
            logger.print_error(f"Error writing file {self.path}: {e}")
            raise

    def exists(self) -> bool:
        """Check if file exists"""
        return os.path.exists(self.path)

    def get_permissions(self) -> Optional[str]:
        """Get file permissions in octal format"""
        try:
            st = os.stat(self.path)
            return oct(stat.S_IMODE(st.st_mode))[-3:]
        except (OSError, FileNotFoundError):
            return None

    def set_permissions(self, permissions: str) -> bool:
        """Set file permissions (octal string like '644')"""
        try:
            os.chmod(self.path, int(permissions, 8))
            return True
        except (OSError, ValueError):
            logger.print_error(
                f"Failed to set permissions {permissions} on {self.path}"
            )
            return False

    def get_owner(self) -> Optional[str]:
        """Get file owner"""
        try:
            import pwd

            st = os.stat(self.path)
            return pwd.getpwuid(st.st_uid).pw_name
        except (OSError, ImportError, KeyError):
            return None

    def get_group(self) -> Optional[str]:
        """Get file group"""
        try:
            import grp

            st = os.stat(self.path)
            return grp.getgrgid(st.st_gid).gr_name
        except (OSError, ImportError, KeyError):
            return None

    def set_owner(self, owner: str, group: str) -> bool:
        """Set file owner and group"""
        try:
            import pwd
            import grp

            uid = pwd.getpwnam(owner).pw_uid
            gid = grp.getgrnam(group).gr_gid
            os.chown(self.path, uid, gid)
            return True
        except (OSError, KeyError, ImportError):
            logger.print_error(f"Failed to set owner {owner}:{group} on {self.path}")
            return False

    def backup(self, backup_suffix: str = ".bak") -> bool:
        """Create a backup of the file"""
        try:
            if self.exists():
                backup_path = self.path + backup_suffix
                shutil.copy2(self.path, backup_path)
                return True
            return False
        except (OSError, shutil.Error):
            logger.print_error(f"Failed to create backup of {self.path}")
            return False

    def restore_backup(self, backup_suffix: str = ".bak") -> bool:
        """Restore file from backup"""
        try:
            backup_path = self.path + backup_suffix
            if os.path.exists(backup_path):
                shutil.copy2(backup_path, self.path)
                return True
            return False
        except (OSError, shutil.Error):
            logger.print_error(f"Failed to restore backup for {self.path}")
            return False

    def validate_structure(self, expected_structure: dict) -> list:
        """Validate file against expected structure"""
        errors = []

        # Check file exists
        if not self.exists():
            errors.append(f"File does not exist: {self.path}")
            return errors

        # Check permissions if specified
        if "permissions" in expected_structure:
            expected_perms = expected_structure["permissions"]
            actual_perms = self.get_permissions()
            if actual_perms != expected_perms:
                errors.append(
                    f"Permissions mismatch: expected {expected_perms}, got {actual_perms}"
                )

        # Check owner if specified
        if "owner" in expected_structure:
            expected_owner = expected_structure["owner"]
            actual_owner = self.get_owner()
            if actual_owner != expected_owner:
                errors.append(
                    f"Owner mismatch: expected {expected_owner}, got {actual_owner}"
                )

        # Check group if specified
        if "group" in expected_structure:
            expected_group = expected_structure["group"]
            actual_group = self.get_group()
            if actual_group != expected_group:
                errors.append(
                    f"Group mismatch: expected {expected_group}, got {actual_group}"
                )

        return errors
