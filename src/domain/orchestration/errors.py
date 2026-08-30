"""
Job/Phase orchestration errors [REQ-ORCH-031, REQ-ORCH-032].
"""


class OrchestrationError(Exception):
    """Base exception for Job/Phase control-plane errors."""


class InvalidJobStatusError(OrchestrationError):
    """Raised when a job or phase status string is not in the locked set."""


class MissingParentJobError(OrchestrationError):
    """Raised when a phase is written without a persisted parent job."""


class JobNotFoundError(OrchestrationError):
    """Raised when a job id is not in SQLite."""


class PhaseNotFoundError(OrchestrationError):
    """Raised when a phase id is not in SQLite."""


class InvalidPhaseTransitionError(OrchestrationError):
    """Raised when a phase or job cannot move to the requested status."""


class HandoffPacketError(OrchestrationError):
    """Missing or invalid HandoffPacket field [REQ-ORCH-036]."""


class ProposalNotFoundError(OrchestrationError):
    """Raised when a proposal id is not in SQLite [REQ-ORCH-043]."""


class InvalidProposalStatusError(OrchestrationError):
    """Raised when a proposal kind/status/decision is not in the locked set."""

