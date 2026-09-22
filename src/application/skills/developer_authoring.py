"""Skill Studio developer-mediated authoring [CARD-420 / ADR-0057].

Build and Review submit a versioned form packet onto a visible standing job
owned by the developer agent. Cheap lint stays in-form and does not mint a job.
Accept and Reject are recorded on that job. Skill bodies and tool bindings
stay on the existing Skill Studio save path.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Iterable, Mapping, Optional

from src.application.skills.linter import SkillContractCompiler
from src.application.skills.runbook_frontmatter import normalize_tool_ids, split_skill_markdown
from src.domain.orchestration.models import HandoffPacket, JobStatus, PhaseSpec

logger = logging.getLogger(__name__)

PACKET_SCHEMA = "skill_studio_authoring_packet"
PACKET_VERSION = 1
PROPOSAL_SCHEMA = "skill_studio_authoring_proposal"
TEMPLATE_ID = "skill_studio_developer_authoring"
DEVELOPER_AGENT_ID = "developer"
PACKET_EVENT_KIND = "skill_studio_authoring_packet"
PROPOSAL_EVENT_KIND = "skill_studio_authoring_proposal"
DECISION_EVENT_KIND = "skill_studio_authoring_decision"
PACKET_FACT_PREFIX = "skill_studio_authoring_packet_json="
PROPOSAL_FACT_PREFIX = "skill_studio_authoring_proposal_json="

ALLOWED_PATCH_FIELDS = frozenset({"name", "description", "tier", "safety", "requires_tools", "markdown"})
VALID_TIERS = frozenset({"platform", "pack", "user"})
_OPEN_STATUSES = frozenset({JobStatus.QUEUED.value, JobStatus.RUNNING.value, JobStatus.WAITING_APPROVAL.value})
_SUCCESS_RULE = (
    "Done-when: proposed field patches are attached for the operator to accept "
    "into the Skill Studio draft. The skill store is unchanged until the operator saves."
)


class AuthoringError(ValueError):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.status_code = status_code


def session_id_for_skill(skill_id: str) -> str:
    return f"skill-studio:{skill_id}"


def _status_value(status: Any) -> str:
    return status.value if hasattr(status, "value") else str(status or "")


def normalize_draft(raw: Optional[Mapping[str, Any]]) -> dict[str, Any]:
    source = dict(raw or {})
    safety_raw = source.get("safety") if isinstance(source.get("safety"), Mapping) else {}
    tools: list[str] = []
    for item in source.get("requires_tools") or []:
        text = str(item).strip()
        if text and text not in tools:
            tools.append(text)
    tier = str(source.get("tier") or "pack").strip().lower() or "pack"
    return {
        "skill_id": str(source.get("skill_id") or "").strip(),
        "name": str(source.get("name") or "").strip(),
        "description": str(source.get("description") or "").strip(),
        "tier": tier,
        "safety": {
            "read_only": bool(safety_raw.get("read_only", False)),
            "requires_hitl": bool(safety_raw.get("requires_hitl", False)),
            "untrusted_input_allowed": bool(safety_raw.get("untrusted_input_allowed", False)),
        },
        "requires_tools": tools,
        "markdown": str(source.get("markdown") if source.get("markdown") is not None else ""),
        "intent_notes": str(source.get("intent_notes") or ""),
        "source_context": str(source.get("source_context") or ""),
    }


def _frontmatter_blockers(markdown: str) -> list[dict[str, Any]]:
    raw = (markdown or "").replace("\r\n", "\n")
    if not raw.strip():
        return [{"code": "FM-EMPTY", "message": "SKILL.md is empty.", "field": "markdown"}]
    if not raw.startswith("---"):
        return [
            {
                "code": "FM-001",
                "message": "SKILL.md is missing YAML frontmatter.",
                "field": "markdown",
            }
        ]
    try:
        meta, _body = split_skill_markdown(raw)
    except Exception as exc:
        return [
            {
                "code": "FM-YAML",
                "message": f"YAML frontmatter parse error: {exc}",
                "field": "markdown",
            }
        ]
    if not meta:
        return [
            {
                "code": "FM-YAML",
                "message": "Malformed YAML frontmatter delimiters.",
                "field": "markdown",
            }
        ]
    blockers: list[dict[str, Any]] = []
    if not str(meta.get("name") or "").strip():
        blockers.append({"code": "FM-NAME", "message": "Frontmatter name is empty.", "field": "name"})
    if not str(meta.get("description") or "").strip():
        blockers.append({"code": "FM-DESC", "message": "Frontmatter description is empty.", "field": "description"})
    return blockers


def cheap_lint_draft(
    draft: Mapping[str, Any],
    catalog_ids: Optional[Iterable[str]] = None,
) -> list[dict[str, Any]]:
    """Frontmatter, catalog tool ids, and the existing contract linter. No LLM."""
    markdown = str(draft.get("markdown") or "")
    blockers = _frontmatter_blockers(markdown)
    catalog = [] if catalog_ids is None else [str(item) for item in catalog_ids]
    _accepted, rejected = normalize_tool_ids(draft.get("requires_tools") or [], catalog)
    if rejected:
        blockers.append(
            {
                "code": "TOOL-UNKNOWN",
                "message": "Unknown catalog tool ids: " + ", ".join(rejected),
                "field": "requires_tools",
                "rejected": rejected,
            }
        )
    _contract, violations = SkillContractCompiler().compile(markdown)
    for violation in violations:
        severity = getattr(violation.severity, "value", violation.severity)
        blockers.append(
            {
                "code": violation.rule_id,
                "message": violation.message,
                "field": "markdown",
                "severity": str(severity),
            }
        )
    return blockers


def build_packet(intent: str, draft: Mapping[str, Any], blockers: list[dict[str, Any]]) -> dict[str, Any]:
    clean_intent = str(intent or "").strip().lower()
    if clean_intent not in {"build", "review"}:
        raise AuthoringError("intent must be build or review")
    normalized = normalize_draft(draft)
    if not normalized["skill_id"]:
        raise AuthoringError("skill_id is required")
    return {
        "schema": PACKET_SCHEMA,
        "version": PACKET_VERSION,
        "studio": "skill",
        "intent": clean_intent,
        "agent_id": DEVELOPER_AGENT_ID,
        "draft": normalized,
        "lint": {"cheap": True, "blockers": blockers},
        "llm_rewrite": False,
    }


def validate_patches(patches: Any) -> list[dict[str, Any]]:
    if not isinstance(patches, list) or not patches:
        raise AuthoringError("patches must be a non-empty list")
    clean: list[dict[str, Any]] = []
    for item in patches:
        if not isinstance(item, Mapping):
            raise AuthoringError("each patch must be an object")
        field = str(item.get("field") or "").strip()
        if field not in ALLOWED_PATCH_FIELDS:
            raise AuthoringError(f"patch field {field!r} is not allowed")
        value = item.get("value")
        if field == "tier":
            tier = str(value or "").strip().lower()
            if tier not in VALID_TIERS:
                raise AuthoringError(f"invalid tier {tier!r}")
            value = tier
        elif field == "safety":
            if not isinstance(value, Mapping):
                raise AuthoringError("safety patch must be an object")
            value = {
                "read_only": bool(value.get("read_only", False)),
                "requires_hitl": bool(value.get("requires_hitl", False)),
                "untrusted_input_allowed": bool(value.get("untrusted_input_allowed", False)),
            }
        elif field == "requires_tools":
            if not isinstance(value, list):
                raise AuthoringError("requires_tools patch must be a list")
            tools: list[str] = []
            for tool in value:
                text = str(tool).strip()
                if text and text not in tools:
                    tools.append(text)
            value = tools
        elif not isinstance(value, str):
            raise AuthoringError(f"{field} patch must be a string")
        clean.append({"field": field, "value": value})
    return clean


def watch_path(job_id: str) -> dict[str, Any]:
    return {
        "primary": "observe",
        "observe": {
            "studio": "observe",
            "tab": "observability",
            "job_id": job_id,
        },
        "chat": {
            "studio": "chat",
            "job_id": job_id,
            "agent_id": DEVELOPER_AGENT_ID,
        },
    }


def _prefixed_json(prefix: str, payload: Mapping[str, Any]) -> str:
    return prefix + json.dumps(payload, separators=(",", ":"), sort_keys=True)


def _handoff_json(goal: str, payload_fact: str) -> str:
    packet = HandoffPacket(
        goal=goal,
        facts=[payload_fact],
        constraints=[
            "Return field patches for the operator to accept into the Skill Studio draft.",
            "Do not persist the skill. The operator saves from Skill Studio.",
        ],
        done_when=_SUCCESS_RULE,
        budget={"max_turns": 8, "max_handoffs": 1, "max_ollama_slots": 1},
    )
    return packet.model_dump_json()


def _load_prefixed(raw_json: Optional[str], prefix: str) -> Optional[dict[str, Any]]:
    if not raw_json:
        return None
    try:
        packet = HandoffPacket.model_validate_json(raw_json)
    except Exception:
        return None
    for fact in packet.facts:
        if str(fact).startswith(prefix):
            try:
                loaded = json.loads(str(fact)[len(prefix) :])
            except json.JSONDecodeError:
                return None
            return loaded if isinstance(loaded, dict) else None
    return None


class DeveloperAuthoringService:
    def __init__(self, store: Any, orchestrator: Any, catalog_ids: Optional[Iterable[str]] = None) -> None:
        self._store = store
        self._orchestrator = orchestrator
        self._catalog_ids = [str(item) for item in (catalog_ids or [])]

    def lint(self, draft: Optional[Mapping[str, Any]]) -> dict[str, Any]:
        normalized = normalize_draft(draft)
        blockers = cheap_lint_draft(normalized, self._catalog_ids)
        return {
            "opened_job": False,
            "job_id": None,
            "llm_rewrite": False,
            "cheap": True,
            "blockers": blockers,
        }

    def submit(self, intent: str, draft: Optional[Mapping[str, Any]]) -> dict[str, Any]:
        normalized = normalize_draft(draft)
        blockers = cheap_lint_draft(normalized, self._catalog_ids)
        packet = build_packet(intent, normalized, blockers)
        existing = self._open_job_for_skill(packet["draft"]["skill_id"])
        resumed = existing is not None
        job = existing or self._create_job(packet)
        self._stamp_packet(job, packet)
        self._record_event(
            job.id,
            PACKET_EVENT_KIND,
            {
                "schema": PACKET_SCHEMA,
                "version": PACKET_VERSION,
                "studio": "skill",
                "intent": packet["intent"],
                "skill_id": packet["draft"]["skill_id"],
                "agent_id": DEVELOPER_AGENT_ID,
                "blocker_count": len(blockers),
                "resumed": resumed,
                "packet": packet,
            },
        )
        logger.info(
            "Skill Studio %s %s developer job %s",
            "resumed" if resumed else "opened",
            packet["intent"],
            job.id,
        )
        return self._job_payload(job, packet=packet, resumed=resumed)

    def get_job(self, job_id: str) -> dict[str, Any]:
        job = self._require_job(job_id)
        packet = self._read_packet(job)
        return self._job_payload(job, packet=packet, resumed=False, include_proposals=True)

    def propose(self, job_id: str, patches: Any) -> dict[str, Any]:
        job = self._require_job(job_id)
        clean = validate_patches(patches)
        proposal = {
            "schema": PROPOSAL_SCHEMA,
            "version": PACKET_VERSION,
            "patches": clean,
            "decision": None,
        }
        phase = self._author_phase(job.id)
        phase.output_packet_json = _handoff_json(
            f"Proposed Skill Studio patches for {job.id}",
            _prefixed_json(PROPOSAL_FACT_PREFIX, proposal),
        )
        self._store.update_phase(phase)
        self._record_event(
            job.id,
            PROPOSAL_EVENT_KIND,
            {"patch_count": len(clean), "fields": [item["field"] for item in clean]},
        )
        return {
            "job_id": job.id,
            "agent_id": DEVELOPER_AGENT_ID,
            "proposals": proposal,
            "persisted_skill": False,
            "llm_rewrite": False,
        }

    def decide(self, job_id: str, decision: str) -> dict[str, Any]:
        job = self._require_job(job_id)
        choice = str(decision or "").strip().lower()
        if choice not in {"accept", "reject"}:
            raise AuthoringError("decision must be accept or reject")
        proposal = self._read_proposal(job) or {
            "schema": PROPOSAL_SCHEMA,
            "version": PACKET_VERSION,
            "patches": [],
            "decision": None,
        }
        patches = list(proposal.get("patches") or [])
        if choice == "accept" and not patches:
            raise AuthoringError("no patches to accept", status_code=409)
        proposal["decision"] = choice
        phase = self._author_phase(job.id)
        phase.output_packet_json = _handoff_json(
            f"Operator {choice} for {job.id}",
            _prefixed_json(PROPOSAL_FACT_PREFIX, proposal),
        )
        self._store.update_phase(phase)
        self._record_event(job.id, DECISION_EVENT_KIND, {"decision": choice, "persisted_skill": False})
        return {
            "job_id": job.id,
            "decision": choice,
            "patches": patches,
            "persisted_skill": False,
            "llm_rewrite": False,
        }

    def _create_job(self, packet: Mapping[str, Any]) -> Any:
        skill_id = packet["draft"]["skill_id"]
        intent = packet["intent"]
        if self._orchestrator is None or not hasattr(self._orchestrator, "create_job_with_phases"):
            raise AuthoringError("standing job orchestrator is unavailable", status_code=503)
        return self._orchestrator.create_job_with_phases(
            goal=f"Skill Studio {intent}: {skill_id}",
            session_id=session_id_for_skill(skill_id),
            agent_id=DEVELOPER_AGENT_ID,
            phase_specs=[
                PhaseSpec(
                    name="Author",
                    success_rule=_SUCCESS_RULE,
                    assigned_agent_id=DEVELOPER_AGENT_ID,
                    verify_checker=None,
                    max_turns=8,
                )
            ],
            template_id=TEMPLATE_ID,
            success_rule=_SUCCESS_RULE,
        )

    def _open_job_for_skill(self, skill_id: str) -> Any:
        lister = getattr(self._store, "list_jobs_for_session", None)
        if not callable(lister):
            return None
        for job in lister(session_id_for_skill(skill_id)) or []:
            template = getattr(job, "template_id", None)
            if template != TEMPLATE_ID:
                continue
            if _status_value(getattr(job, "status", "")) in _OPEN_STATUSES:
                return job
        return None

    def _require_job(self, job_id: str) -> Any:
        getter = getattr(self._store, "get_job", None)
        if not callable(getter):
            raise AuthoringError("job store is unavailable", status_code=503)
        try:
            job = getter(str(job_id or "").strip())
        except Exception as exc:
            raise AuthoringError(f"Job {job_id} not found.", status_code=404) from exc
        if job is None or getattr(job, "template_id", None) != TEMPLATE_ID:
            raise AuthoringError(f"Job {job_id} not found.", status_code=404)
        if getattr(job, "agent_id", None) != DEVELOPER_AGENT_ID:
            raise AuthoringError(f"Job {job_id} not found.", status_code=404)
        return job

    def _author_phase(self, job_id: str) -> Any:
        phases = list(self._store.list_phases_for_job(job_id) or [])
        if not phases:
            raise AuthoringError(f"Job {job_id} has no author phase.", status_code=404)
        return phases[0]

    def _stamp_packet(self, job: Any, packet: Mapping[str, Any]) -> None:
        phase = self._author_phase(job.id)
        phase.input_packet_json = _handoff_json(
            f"Skill Studio {packet['intent']}: {packet['draft']['skill_id']}",
            _prefixed_json(PACKET_FACT_PREFIX, packet),
        )
        phase.assigned_agent_id = DEVELOPER_AGENT_ID
        self._store.update_phase(phase)

    def _read_packet(self, job: Any) -> Optional[dict[str, Any]]:
        phase = self._author_phase(job.id)
        return _load_prefixed(getattr(phase, "input_packet_json", None), PACKET_FACT_PREFIX)

    def _read_proposal(self, job: Any) -> Optional[dict[str, Any]]:
        phase = self._author_phase(job.id)
        return _load_prefixed(getattr(phase, "output_packet_json", None), PROPOSAL_FACT_PREFIX)

    def _record_event(self, job_id: str, kind: str, payload: Mapping[str, Any]) -> None:
        saver = getattr(self._store, "save_standing_journey_event", None)
        if callable(saver):
            saver(job_id=job_id, kind=kind, payload=dict(payload))

    def _job_payload(
        self,
        job: Any,
        *,
        packet: Optional[Mapping[str, Any]],
        resumed: bool,
        include_proposals: bool = False,
    ) -> dict[str, Any]:
        body = {
            "job_id": job.id,
            "agent_id": DEVELOPER_AGENT_ID,
            "status": _status_value(getattr(job, "status", "")),
            "template_id": TEMPLATE_ID,
            "resumed": resumed,
            "visible": True,
            "llm_rewrite": False,
            "persisted_skill": False,
            "packet": dict(packet) if packet else None,
            "watch": watch_path(job.id),
        }
        if include_proposals:
            body["proposals"] = self._read_proposal(job)
        return body
