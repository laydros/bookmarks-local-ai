"""
Backup and safety utilities for bookmark processing.
"""

import os
import shutil
import json
import time
from datetime import datetime
from typing import List, Optional, Dict
import logging

logger = logging.getLogger(__name__)


class BackupManager:
    """Manages backups of bookmark files."""

    def __init__(
        self,
        backup_dir: str = "backups",
        keep_backups: int = 10,
        backup_suffix: str = ".backup",
    ):
        """
        Initialize backup manager.

        Args:
            backup_dir: Directory to store backups
            keep_backups: Number of backups to keep per file
            backup_suffix: Suffix for backup files
        """
        self.backup_dir = backup_dir
        self.keep_backups = keep_backups
        self.backup_suffix = backup_suffix

        # Create backup directory if it doesn't exist
        if not os.path.exists(self.backup_dir):
            os.makedirs(self.backup_dir)
            logger.info(f"Created backup directory: {self.backup_dir}")

    def create_backup(
        self, file_path: str, backup_name: Optional[str] = None
    ) -> Optional[str]:
        """
        Create a backup of a file.

        Args:
            file_path: Path to file to backup
            backup_name: Optional custom backup name

        Returns:
            Path to backup file if successful, None otherwise
        """
        if not os.path.exists(file_path):
            logger.error(f"Cannot backup non-existent file: {file_path}")
            return None

        try:
            # Generate backup filename
            if backup_name is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                base_name = os.path.basename(file_path)
                backup_name = f"{timestamp}_{base_name}{self.backup_suffix}"

            backup_path = os.path.join(self.backup_dir, backup_name)

            # Copy file to backup location
            shutil.copy2(file_path, backup_path)

            logger.info(f"Created backup: {backup_path}")

            # Clean up old backups
            self._cleanup_old_backups(os.path.basename(file_path))

            return backup_path

        except Exception as e:
            logger.error(f"Failed to create backup of {file_path}: {e}")
            return None

    def create_directory_backup(self, directory_path: str) -> Optional[str]:
        """
        Create backups of all JSON files in a directory.

        Args:
            directory_path: Directory containing files to backup

        Returns:
            Backup directory path if successful, None otherwise
        """
        if not os.path.isdir(directory_path):
            logger.error(f"Cannot backup non-existent directory: {directory_path}")
            return None

        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_subdir = os.path.join(
                self.backup_dir, f"directory_backup_{timestamp}"
            )
            os.makedirs(backup_subdir)

            json_files = [f for f in os.listdir(directory_path) if f.endswith(".json")]

            if not json_files:
                logger.warning(f"No JSON files found in {directory_path}")
                os.rmdir(backup_subdir)
                return None

            backup_count = 0
            for json_file in json_files:
                source_path = os.path.join(directory_path, json_file)
                backup_path = os.path.join(backup_subdir, json_file)

                shutil.copy2(source_path, backup_path)
                backup_count += 1

            logger.info(
                f"Created directory backup: {backup_subdir} ({backup_count} files)"
            )
            return backup_subdir

        except Exception as e:
            logger.error(f"Failed to create directory backup of {directory_path}: {e}")
            return None

    def restore_backup(self, backup_path: str, target_path: str) -> bool:
        """
        Restore a file from backup.

        Args:
            backup_path: Path to backup file
            target_path: Path where to restore the file

        Returns:
            True if successful, False otherwise
        """
        if not os.path.exists(backup_path):
            logger.error(f"Backup file not found: {backup_path}")
            return False

        try:
            shutil.copy2(backup_path, target_path)
            logger.info(f"Restored {backup_path} to {target_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to restore backup {backup_path}: {e}")
            return False

    def list_backups(self, original_filename: Optional[str] = None) -> List[Dict]:
        """
        List available backups.

        Args:
            original_filename: If provided, only show backups for this file

        Returns:
            List of backup info dictionaries
        """
        backups = []

        try:
            for item in os.listdir(self.backup_dir):
                item_path = os.path.join(self.backup_dir, item)

                if os.path.isfile(item_path) and item.endswith(self.backup_suffix):
                    # Parse backup filename
                    if original_filename:
                        if not item.endswith(
                            f"{original_filename}{self.backup_suffix}"
                        ):
                            continue

                    stat = os.stat(item_path)
                    backup_info = {
                        "filename": item,
                        "path": item_path,
                        "size": stat.st_size,
                        "created": datetime.fromtimestamp(stat.st_mtime),
                        "original_file": self._extract_original_filename(item),
                    }
                    backups.append(backup_info)

            # Sort by creation time (newest first)
            backups.sort(key=lambda x: x["created"], reverse=True)

        except Exception as e:
            logger.error(f"Error listing backups: {e}")

        return backups

    def _extract_original_filename(self, backup_filename: str) -> str:
        """Extract original filename from backup filename."""
        if backup_filename.endswith(self.backup_suffix):
            without_suffix = backup_filename[: -len(self.backup_suffix)]
            # Remove timestamp prefix (YYYYMMDD_HHMMSS_)
            parts = without_suffix.split("_", 2)
            if len(parts) >= 3:
                return parts[2]
            return without_suffix
        return backup_filename

    def _cleanup_old_backups(self, original_filename: str):
        """Remove old backups, keeping only the specified number."""
        backups = self.list_backups(original_filename)

        if len(backups) > self.keep_backups:
            backups_to_remove = backups[self.keep_backups :]

            for backup in backups_to_remove:
                try:
                    os.remove(backup["path"])
                    logger.debug(f"Removed old backup: {backup['filename']}")
                except Exception as e:
                    logger.warning(
                        f"Failed to remove old backup {backup['filename']}: {e}"
                    )

    def get_backup_stats(self) -> Dict:
        """Get statistics about backups."""
        try:
            backups = self.list_backups()
            total_size = sum(backup["size"] for backup in backups)

            return {
                "total_backups": len(backups),
                "total_size_bytes": total_size,
                "total_size_mb": total_size / (1024 * 1024),
                "backup_dir": self.backup_dir,
                "oldest_backup": min(backups, key=lambda x: x["created"])["created"]
                if backups
                else None,
                "newest_backup": max(backups, key=lambda x: x["created"])["created"]
                if backups
                else None,
            }
        except Exception as e:
            logger.error(f"Error getting backup stats: {e}")
            return {}


def create_safety_backup(
    file_or_dir: str, backup_manager: Optional[BackupManager] = None
) -> Optional[str]:
    """
    Create a safety backup before processing.

    Args:
        file_or_dir: File or directory to backup
        backup_manager: Optional backup manager instance

    Returns:
        Backup path if successful, None otherwise
    """
    if backup_manager is None:
        backup_manager = BackupManager()

    if os.path.isfile(file_or_dir):
        return backup_manager.create_backup(file_or_dir)
    elif os.path.isdir(file_or_dir):
        return backup_manager.create_directory_backup(file_or_dir)
    else:
        logger.error(f"Cannot backup: {file_or_dir} is neither file nor directory")
        return None
