"""
Conditional Capability Graph Orchestrator & The Rinse Loop [REQ-FACT-004, REQ-FACT-010, REQ-FACT-011, REQ-FACT-015].

Implements the deterministic state graph engine, tool consolidation heuristics,
agent split policies, and portable User Agent Pack finalization.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.infrastructure.memory.repositories.factory_packets import FactoryPacketRepository

GRAPH_TRANSITIONS: Dict[str, Dict[str, str]] = {
    "socratic_handshake": {
        "ok": "discovery_probe",
    },
    "discovery_probe": {
        "ok": "architecture_blueprint",
        "fail": "socratic_handshake",
    },
    "architecture_blueprint": {
        "ok": "attempt_node",
    },
    "attempt_node": {
        "ok": "critic_signoff_node",
        "need_capability": "conduct_node",
        "need_human": "hitl_deploy_gate_node",
        "fail": "conduct_node",
    },
    "conduct_node": {
        "ok": "coder_node",
        "fail": "attempt_node",
    },
    "coder_node": {
        "ok": "sandbox_battery_node",
        "fail": "conduct_node",
    },
    "sandbox_battery_node": {
        "ok": "attempt_node",
        "fail": "conduct_node",
    },
    "critic_signoff_node": {
        "ok": "hitl_deploy_gate_node",
        "fail": "conduct_node",
    },
    "hitl_deploy_gate_node": {
        "ok": "pack_finalized_node",
        "approved": "pack_finalized_node",
        "rejected": "failed",
    },
    "pack_finalized_node": {},
}


class CapabilityGraphEngine:
    """
    Deterministic graph walker advancing training jobs between phase nodes [REQ-FACT-004].
    """

    def __init__(self, repo: FactoryPacketRepository):
        self.repo = repo

    def advance(self, job_id: str, outcome: str = "ok") -> str:
        job = self.repo.get_job(job_id)
        if not job:
            raise ValueError(f"Factory job {job_id} not found")

        current_node = job.current_node_id
        transitions = GRAPH_TRANSITIONS.get(current_node, {})

        if outcome not in transitions:
            # Default to "ok" if present, or raise transition error
            if "ok" in transitions:
                next_node = transitions["ok"]
            else:
                raise ValueError(
                    f"Invalid outcome '{outcome}' from node '{current_node}'. Allowed: {list(transitions.keys())}"
                )
        else:
            next_node = transitions[outcome]

        new_status = "running"
        if next_node == "pack_finalized_node":
            new_status = "done"
        elif next_node == "hitl_deploy_gate_node":
            new_status = "waiting_approval"
        elif next_node == "failed":
            new_status = "failed"

        self.repo.update_job_status(
            job_id=job_id,
            status=new_status,
            current_node_id=next_node,
            cycles_consumed=job.cycles_consumed + 1,
        )
        return next_node


class ToolConsolidationGate:
    """
    Prevents tool bloat by merging related verbs into unified action dispatchers [REQ-FACT-010].
    """

    def evaluate(self, proposed_tools: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Evaluate proposed tools and recommend consolidation if multiple single-verb
        tools target the same underlying entity or resource.
        """
        by_entity: Dict[str, List[Dict[str, Any]]] = {}
        for tool in proposed_tools:
            entity = tool.get("target_entity") or "general"
            by_entity.setdefault(entity, []).append(tool)

        for entity, tools in by_entity.items():
            if len(tools) >= 2:
                verbs = [t.get("verb") or t.get("name", "").split("_")[0] for t in tools]
                return {
                    "should_consolidate": True,
                    "target_entity": entity,
                    "suggested_tool_name": f"manage_{entity}",
                    "actions": sorted(list(set(verbs))),
                    "reason": f"Merged {len(tools)} single-verb tools targeting entity '{entity}' into one dispatcher.",
                }

        return {
            "should_consolidate": False,
            "target_entity": "",
            "suggested_tool_name": "",
            "actions": [],
            "reason": "No common entity tool bloat detected.",
        }


class AgentSplitPolicy:
    """
    Enforces specialist focus and proposes role divisions when domain boundaries sprawl [REQ-FACT-011].
    """

    def evaluate_split(
        self, agent_id: str, tools: List[Dict[str, Any]], max_tools_per_agent: int = 6
    ) -> Dict[str, Any]:
        """
        Detects domain sprawl across distinct administrative domains.
        """
        by_domain: Dict[str, List[Dict[str, Any]]] = {}
        for tool in tools:
            domain = tool.get("domain") or "default"
            by_domain.setdefault(domain, []).append(tool)

        # Trigger split if >= 2 distinct non-default domains are present
        if len(by_domain) >= 2:
            proposals = []
            for domain, domain_tools in by_domain.items():
                split_agent_id = f"{agent_id}-{domain.replace('_', '-')}"
                proposals.append(
                    {
                        "domain": domain,
                        "proposed_agent_id": split_agent_id,
                        "tools": [t.get("name") for t in domain_tools],
                    }
                )

            return {
                "should_split": True,
                "split_proposals": proposals,
                "recommended_contract": "handoff_to_agent",
                "reason": f"Agent {agent_id} crosses {len(by_domain)} distinct operational domains. Splitting into focused packs.",
            }

        return {
            "should_split": False,
            "split_proposals": [],
            "recommended_contract": None,
            "reason": "Agent responsibilities are properly cohesive within a single domain.",
        }


class UserPackFinalizer:
    """
    Strictly writes completed, verified tools and runbooks to User Agent Packs ($DATA_DIR/packs/<agent_id>/) [REQ-FACT-001, REQ-FACT-015].
    """

    def __init__(self, data_dir: Optional[str] = None):
        self.data_dir = Path(data_dir or "./data").resolve()

    def finalize_pack(
        self,
        agent_id: str,
        manifest_data: Dict[str, Any],
        files: Dict[str, str],
    ) -> str:
        """
        Persist pack.json, Python tools, and skill runbooks into $DATA_DIR/packs/<agent_id>/.
        Never pollutes platform-packs/ or central platform directories.
        """
        pack_dir = self.data_dir / "packs" / agent_id
        pack_dir.mkdir(parents=True, exist_ok=True)

        manifest_data.setdefault("schema_version", "1.1")
        manifest_data.setdefault("id", agent_id)
        manifest_data.setdefault("show_in_chat", True)

        manifest_file = pack_dir / "pack.json"
        manifest_file.write_text(json.dumps(manifest_data, indent=2), encoding="utf-8")

        for rel_path, content in files.items():
            out_file = pack_dir / rel_path
            out_file.parent.mkdir(parents=True, exist_ok=True)
            out_file.write_text(content, encoding="utf-8")

        return str(pack_dir)
