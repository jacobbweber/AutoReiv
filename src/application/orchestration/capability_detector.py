"""
Capability Gap Detection [REQ-FACT-024, REQ-FACT-027].
Identifies turn-time missing tools or capability deficiencies from agent responses.
"""

import re
from typing import Optional

from pydantic import BaseModel, Field


class CapabilityGapDetection(BaseModel):
    """Structured detection of a missing tool or capability gap."""
    detected: bool = True
    missing_capability: str = Field(..., description="Description of the missing capability")
    suggested_tool_name: str = Field(..., description="Suggested identifier for the synthesized tool")
    user_prompt: str = Field(default="", description="Original user prompt that triggered the gap")
    context_summary: str = Field(default="", description="Relevant context or error summary")


class CapabilityDetector:
    """
    Analyzes user prompts and assistant responses to detect turn-time capability gaps.
    """

    PATTERNS = [
        re.compile(r"(?:don't|do not|cannot|can't|unable to|lack(?:s)?)\s+(?:have|find|access|possess)?\s*(?:the\s+)?(?:tools?|capability|capabilities|ability|command|permission)\s+(?:to|for)?\s*(.+?)(?:\.|$)", re.IGNORECASE),
        re.compile(r"I don't have (?:a|any|the)?\s*tools?\s*(?:to|for)?\s*(.+?)(?:\.|$)", re.IGNORECASE),
        re.compile(r"I cannot directly (?:create|manage|execute|run|provision|delete|modify)\s+(.+?)(?:\.|$)", re.IGNORECASE),
        re.compile(r"no tool available to (.+?)(?:\.|$)", re.IGNORECASE),
        re.compile(r"unable to (.+?) without a tool", re.IGNORECASE),
        re.compile(r"without a tool to (.+?)(?:\.|$)", re.IGNORECASE),
    ]

    GREETINGS = {"hi", "hello", "hey", "thanks", "thank you", "good morning", "good evening"}

    RETRY_PROMPTS = {
        "can you try again", "try again", "retry", "try it again",
        "please try again", "try once more", "again", "retry that",
        "can you retry", "do it again", "try",
    }

    @classmethod
    def detect(cls, user_prompt: Optional[str], assistant_response: Optional[str]) -> Optional[CapabilityGapDetection]:
        if not user_prompt or not assistant_response:
            return None

        prompt_clean = user_prompt.strip()
        if prompt_clean.lower() in cls.GREETINGS or len(prompt_clean) < 4:
            return None

        for pat in cls.PATTERNS:
            match = pat.search(assistant_response)
            if match:
                extracted = match.group(1).strip().strip(".")
                if not extracted or len(extracted) < 2:
                    extracted = prompt_clean

                # Generate clean suggested tool name
                suggested_tool = cls._suggest_tool_name(extracted, prompt_clean)

                return CapabilityGapDetection(
                    detected=True,
                    missing_capability=extracted,
                    suggested_tool_name=suggested_tool,
                    user_prompt=prompt_clean,
                    context_summary=assistant_response.strip(),
                )

        return None

    @classmethod
    def extract_capabilities_from_turn(
        cls,
        user_prompt: Optional[str],
        assistant_response: Optional[str],
        agent_id: str = "",
        agent_name: str = "",
    ) -> dict:
        """
        Synthesizes technical capabilities and starter objectives from a conversation turn.
        Examines user intent and assistant code/commands rather than raw literal phrases.
        """
        resp_text = (assistant_response or "").strip()
        prompt_text = (user_prompt or "").strip()

        # 1. Check for PowerShell cmdlets in the assistant's response
        ps_cmdlets = re.findall(
            r"\b(New-[A-Za-z0-9]+|Set-[A-Za-z0-9]+|Get-[A-Za-z0-9]+|Add-[A-Za-z0-9]+|Remove-[A-Za-z0-9]+|Start-[A-Za-z0-9]+|Stop-[A-Za-z0-9]+|Enable-[A-Za-z0-9]+|Disable-[A-Za-z0-9]+)\b",
            resp_text,
        )
        unique_cmdlets = list(dict.fromkeys(ps_cmdlets))

        # Check for Docker / CLI commands
        cli_match = re.findall(
            r"\b(docker|kubectl|systemctl|git|npm|pip|cargo|terraform|ansible|az|aws|gcloud)\s+([a-z0-9_-]+)",
            resp_text,
            re.IGNORECASE,
        )

        # Determine effective user action if prompt was a retry phrase
        clean_prompt = prompt_text
        if clean_prompt.lower() in cls.RETRY_PROMPTS or len(clean_prompt) < 4:
            action_match = re.search(
                r"(?:To|can|could)\s+(create|manage|provision|run|start|stop|deploy|configure)\s+[\"']?([a-zA-Z0-9_-]+)[\"']?",
                resp_text,
                re.IGNORECASE,
            )
            if action_match:
                clean_prompt = f"{action_match.group(1).capitalize()} {action_match.group(2)}"
            elif unique_cmdlets:
                clean_prompt = f"Execute {unique_cmdlets[0]}"
            else:
                clean_prompt = f"Automate {agent_name or agent_id or 'operations'}"

        # 2. Build synthesized capability title and objectives
        objectives = []
        if unique_cmdlets:
            display_agent = agent_name or agent_id or "PowerShell"
            if any("VM" in c or "VHD" in c for c in unique_cmdlets):
                cap_title = f"{display_agent} Virtual Machine & Storage Management"
                tool_slug = f"{agent_id or 'hyperv'}_vm_manager"
                objectives = [
                    f"Create, configure, and inspect virtual machines ({', '.join([c for c in unique_cmdlets if 'VM' in c and not 'HardDisk' in c and not 'Switch' in c][:2]) or 'New-VM'})",
                    f"Manage virtual hard disks and storage ({', '.join([c for c in unique_cmdlets if 'VHD' in c or 'HardDisk' in c][:2]) or 'New-VHD'})",
                ]
                switch_cmdlets = [c for c in unique_cmdlets if "Switch" in c or "Net" in c]
                if switch_cmdlets:
                    objectives.append(f"Configure virtual switches and networking ({switch_cmdlets[0]})")
                else:
                    objectives.append("Report VM state and resource allocations")
            else:
                cmd_sample = ", ".join(unique_cmdlets[:3])
                cap_title = f"{display_agent} Operations ({cmd_sample})"
                tool_slug = f"{agent_id or 'ps'}_operations"
                objectives = [
                    f"Execute administrative operations ({cmd_sample})",
                    "Query and verify resource state",
                ]
        elif cli_match:
            base_cli = cli_match[0][0].lower()
            cap_title = f"{base_cli.capitalize()} Operations & Deployment"
            tool_slug = f"{base_cli}_executor"
            subcmds = list(dict.fromkeys([m[1] for m in cli_match[:3]]))
            objectives = [
                f"Run and inspect {base_cli} workloads ({', '.join(subcmds)})",
                f"Manage {base_cli} lifecycle and configuration safely",
            ]
        else:
            det = cls.detect(clean_prompt, resp_text)
            missing = det.missing_capability if det else clean_prompt
            tool_slug = det.suggested_tool_name if det else cls._suggest_tool_name(missing, clean_prompt)
            cap_title = f"{agent_name or agent_id.capitalize() or 'Agent'} Capability: {missing[:50]}"
            objectives = [
                f"Execute {missing[:60]}",
                "Validate operation outcome and report status",
            ]

        tool_slug = re.sub(r"[^a-z0-9_]+", "_", tool_slug.lower()).strip("_")
        if not tool_slug.startswith(("manage_", "create_", "run_", "get_", "hyperv_", "docker_")):
            tool_slug = f"manage_{tool_slug}"

        turn_desc = "\n".join([f"- {o}" for o in objectives])

        return {
            "identified_capability": cap_title,
            "suggested_tool_name": tool_slug,
            "turn_text": turn_desc,
            "objectives": objectives,
            "context_summary": resp_text[:500],
        }

    @classmethod
    async def analyze_turn_with_llm(
        cls,
        user_prompt: str,
        assistant_response: str,
        agent_id: str,
        agent_name: str = "",
        gateway: Optional[object] = None,
    ) -> dict:
        """
        Uses LLM Gateway if available to perform structured semantic gap analysis,
        falling back gracefully to extract_capabilities_from_turn if offline or timed out.
        """
        fallback = cls.extract_capabilities_from_turn(
            user_prompt=user_prompt,
            assistant_response=assistant_response,
            agent_id=agent_id,
            agent_name=agent_name,
        )
        if gateway is None:
            return fallback

        import asyncio
        import json
        from src.domain.gateway.models import ChatMessage, CompletionRequest, Role

        system_msg = (
            "You are an expert capability synthesizer for an autonomous agent platform. "
            "An agent was asked to perform an action but lacked the tools or execution permissions. "
            "Extract a concise technical capability name, a snake_case suggested tool name, and 2-3 specific bullet objectives. "
            "Return ONLY a JSON object with keys: 'identified_capability', 'suggested_tool_name', 'objectives' (list of strings)."
        )
        user_msg = (
            f"Agent: {agent_name or agent_id}\n"
            f"User Intent: {user_prompt}\n"
            f"Assistant Output: {assistant_response[:1200]}\n"
        )

        try:
            req = CompletionRequest(
                model=getattr(gateway, "default_model_id", None) or "default",
                messages=[
                    ChatMessage(role=Role.SYSTEM, content=system_msg),
                    ChatMessage(role=Role.USER, content=user_msg),
                ],
                temperature=0.2,
                max_tokens=250,
            )
            resp = await asyncio.wait_for(gateway.complete(req), timeout=4.0)
            text = resp.text.strip()
            json_match = re.search(r"\{[\s\S]*\}", text)
            if json_match:
                data = json.loads(json_match.group(0))
                cap = data.get("identified_capability")
                tool = data.get("suggested_tool_name")
                objs = data.get("objectives", [])
                if cap and tool and isinstance(objs, list) and len(objs) > 0:
                    return {
                        "identified_capability": str(cap),
                        "suggested_tool_name": re.sub(r"[^a-z0-9_]+", "_", str(tool).lower()).strip("_"),
                        "turn_text": "\n".join([f"- {o}" for o in objs]),
                        "objectives": [str(o) for o in objs],
                        "context_summary": assistant_response[:500],
                    }
        except Exception:
            pass

        return fallback

    @classmethod
    def _suggest_tool_name(cls, capability_text: str, fallback_prompt: str) -> str:
        text = capability_text if len(capability_text) > 3 else fallback_prompt
        text = re.sub(r"\b(a|an|the|directly|to|for|in|on|with)\b", "", text, flags=re.IGNORECASE)
        slug = re.sub(r"[^a-zA-Z0-9]+", "_", text).strip("_").lower()
        parts = [p for p in slug.split("_") if p][:4]
        if not parts:
            return "manage_resource"

        name = "_".join(parts)
        if not name.startswith(("manage_", "create_", "get_", "run_", "delete_")):
            name = f"manage_{name}"
        if name[0].isdigit():
            name = f"tool_{name}"
        return name
