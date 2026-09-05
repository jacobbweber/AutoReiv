"""
SQLite State Store with WAL Mode Facade [REQ-KERNEL-004].
Composes domain repository mixins with thread-safe connection management.
"""

from typing import Optional

from src.infrastructure.memory.connection import SQLiteConnectionManager
from src.infrastructure.memory.repositories.approvals import ApprovalRepositoryMixin
from src.infrastructure.memory.repositories.artifacts import ArtifactRepositoryMixin
from src.infrastructure.memory.repositories.factory_packets import FactoryPacketRepositoryMixin
from src.infrastructure.memory.repositories.facts import FactRepositoryMixin
from src.infrastructure.memory.repositories.jobs import JobRepositoryMixin
from src.infrastructure.memory.repositories.prompts import PromptRepositoryMixin
from src.infrastructure.memory.repositories.proposals import ProposalRepositoryMixin
from src.infrastructure.memory.repositories.routines import RoutineRepositoryMixin
from src.infrastructure.memory.repositories.sessions import SessionRepositoryMixin
from src.infrastructure.memory.repositories.settings import SettingsRepositoryMixin
from src.infrastructure.memory.repositories.tasks import TaskRepositoryMixin
from src.infrastructure.memory.repositories.telemetry import TelemetryRepositoryMixin
from src.infrastructure.memory.repositories.tones import TonesRepositoryMixin


class SQLiteStateStore(
    SQLiteConnectionManager,
    SessionRepositoryMixin,
    ArtifactRepositoryMixin,
    FactRepositoryMixin,
    SettingsRepositoryMixin,
    RoutineRepositoryMixin,
    TelemetryRepositoryMixin,
    ApprovalRepositoryMixin,
    TaskRepositoryMixin,
    JobRepositoryMixin,
    ProposalRepositoryMixin,
    TonesRepositoryMixin,
    PromptRepositoryMixin,
    FactoryPacketRepositoryMixin,
):
    """
    Unified SQLite State Store facade providing thread-safe WAL connection
    management and domain repository capabilities across all AutoReiv subsystems.
    """

    def __init__(self, db_path: Optional[str] = None):
        super().__init__(db_path=db_path)
