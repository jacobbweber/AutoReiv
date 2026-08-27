"""
SQLite State Store with WAL Mode Façade [REQ-KERNEL-004].
Composes domain repository mixins with thread-safe connection management.
"""

from src.infrastructure.memory.connection import SQLiteConnectionManager
from src.infrastructure.memory.repositories.approvals import ApprovalRepositoryMixin
from src.infrastructure.memory.repositories.facts import FactRepositoryMixin
from src.infrastructure.memory.repositories.routines import RoutineRepositoryMixin
from src.infrastructure.memory.repositories.sessions import SessionRepositoryMixin
from src.infrastructure.memory.repositories.settings import SettingsRepositoryMixin
from src.infrastructure.memory.repositories.tasks import TaskRepositoryMixin
from src.infrastructure.memory.repositories.telemetry import TelemetryRepositoryMixin


class SQLiteStateStore(
    SQLiteConnectionManager,
    SessionRepositoryMixin,
    FactRepositoryMixin,
    SettingsRepositoryMixin,
    RoutineRepositoryMixin,
    TelemetryRepositoryMixin,
    ApprovalRepositoryMixin,
    TaskRepositoryMixin,
):
    """
    Unified SQLite State Store façade providing thread-safe WAL connection
    management and domain repository capabilities across all AutoReiv subsystems.
    """

    def __init__(self, db_path: str = "autoreiv.db"):
        super().__init__(db_path=db_path)
