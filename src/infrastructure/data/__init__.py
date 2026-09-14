"""User data directory resolver and backup [REQ-DATA-001 - REQ-DATA-008]."""

from src.infrastructure.data.backup import DataDirBackupService, DataDirRestoreError
from src.infrastructure.data.migrate import (
    DataDirMigrateResult,
    DataDirRelocateError,
    migrate_data_dir,
    persist_autoreiv_data_dir,
    resolve_paths_for_root,
)
from src.infrastructure.data.resolver import (
    DATA_DIR_SETTING_KEY,
    DataDirMigrationError,
    DataDirPaths,
    DataDirResolver,
    bootstrap_data_dir,
    repo_root,
)

__all__ = [
    "DATA_DIR_SETTING_KEY",
    "DataDirBackupService",
    "DataDirMigrateResult",
    "DataDirMigrationError",
    "DataDirRelocateError",
    "DataDirRestoreError",
    "DataDirPaths",
    "DataDirResolver",
    "bootstrap_data_dir",
    "migrate_data_dir",
    "persist_autoreiv_data_dir",
    "repo_root",
    "resolve_paths_for_root",
]
