"""
Settings, Agent Profiles & Overrides Repository Mixin [REQ-SET-001, REQ-FORGE-006].
"""

import json
from datetime import datetime, timezone
from typing import Any, List, Optional

from src.domain.kernel.models import AgentProfile, AgentTone
from src.domain.settings.models import AgentCustomization, ModelPurpose


class SettingsRepositoryMixin:
    """Methods for persisting JSON key-value configurations, agent profiles, and overrides."""

    def set_setting(self, key: str, value: Any) -> None:
        now_str = datetime.now(timezone.utc).isoformat()
        val_json = json.dumps(value)
        conn = self._get_connection()
        try:
            conn.execute(
                """
                INSERT INTO settings (key, value_json, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    value_json = excluded.value_json,
                    updated_at = excluded.updated_at
                """,
                (key, val_json, now_str),
            )
            conn.commit()
        finally:
            if self._mem_conn is None:
                conn.close()

    def get_setting(self, key: str, default: Any = None) -> Any:
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT value_json FROM settings WHERE key = ?", (key,))
            row = cur.fetchone()
            if not row:
                return default
            return json.loads(row["value_json"])
        finally:
            if self._mem_conn is None:
                conn.close()

    def save_agent_override(self, customization: AgentCustomization) -> None:
        now_str = datetime.now(timezone.utc).isoformat()
        tools_json = (
            json.dumps(customization.allowed_tool_names) if customization.allowed_tool_names is not None else None
        )
        skills_json = json.dumps(customization.allowed_skill) if customization.allowed_skill is not None else None
        pack_tools_json = (
            json.dumps(customization.pack_tool_names) if customization.pack_tool_names is not None else None
        )
        show_in_chat = None if customization.show_in_chat is None else (1 if customization.show_in_chat else 0)
        provider_val = getattr(customization, "provider", None) or "default"
        conn = self._get_connection()
        try:
            conn.execute(
                """
                INSERT INTO agent_overrides (
                    agent_id, provider, api_base_url, api_key, context_window, tone, system_prompt, model, purpose,
                    allowed_tools_json, allowed_skills_json, pack_tools_json, show_in_chat, max_turns, history_retention_days,
                    storage_enabled, storage_type, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(agent_id) DO UPDATE SET
                    provider = excluded.provider,
                    api_base_url = excluded.api_base_url,
                    api_key = excluded.api_key,
                    context_window = excluded.context_window,
                    tone = excluded.tone,
                    system_prompt = excluded.system_prompt,
                    model = excluded.model,
                    purpose = excluded.purpose,
                    allowed_tools_json = excluded.allowed_tools_json,
                    allowed_skills_json = excluded.allowed_skills_json,
                    pack_tools_json = excluded.pack_tools_json,
                    show_in_chat = excluded.show_in_chat,
                    max_turns = excluded.max_turns,
                    history_retention_days = excluded.history_retention_days,
                    storage_enabled = excluded.storage_enabled,
                    storage_type = excluded.storage_type,
                    updated_at = excluded.updated_at
                """,
                (
                    customization.agent_id,
                    provider_val,
                    getattr(customization, "api_base_url", None),
                    getattr(customization, "api_key", None),
                    getattr(customization, "context_window", None),
                    customization.tone,
                    customization.system_prompt,
                    customization.model,
                    customization.purpose,
                    tools_json,
                    skills_json,
                    pack_tools_json,
                    show_in_chat,
                    customization.max_turns,
                    customization.history_retention_days,
                    1 if getattr(customization, "storage_enabled", False) else 0,
                    getattr(customization, "storage_type", "sqlite") or "sqlite",
                    now_str,
                ),
            )
            conn.commit()
        finally:
            if self._mem_conn is None:
                conn.close()

    def get_agent_override(self, agent_id: str) -> Optional[AgentCustomization]:
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT agent_id, provider, api_base_url, api_key, context_window, tone, system_prompt, model, purpose,
                       allowed_tools_json, allowed_skills_json, pack_tools_json, show_in_chat, max_turns, history_retention_days,
                       storage_enabled, storage_type
                FROM agent_overrides WHERE agent_id = ?
                """,
                (agent_id,),
            )
            r = cur.fetchone()
            if not r:
                return None
            tools = json.loads(r["allowed_tools_json"]) if r["allowed_tools_json"] else None
            skills = None
            if "allowed_skills_json" in r.keys() and r["allowed_skills_json"]:
                skills = json.loads(r["allowed_skills_json"])
            pack_tools = None
            if "pack_tools_json" in r.keys() and r["pack_tools_json"]:
                pack_tools = json.loads(r["pack_tools_json"])
            show_in_chat = None
            if "show_in_chat" in r.keys() and r["show_in_chat"] is not None:
                show_in_chat = bool(r["show_in_chat"])
            purpose = r["purpose"] if "purpose" in r.keys() else None
            provider = r["provider"] if "provider" in r.keys() and r["provider"] else "default"
            api_base_url = r["api_base_url"] if "api_base_url" in r.keys() else None
            api_key = r["api_key"] if "api_key" in r.keys() else None
            context_window = r["context_window"] if "context_window" in r.keys() else None
            storage_enabled = bool(r["storage_enabled"]) if "storage_enabled" in r.keys() and r["storage_enabled"] is not None else None
            storage_type = r["storage_type"] if "storage_type" in r.keys() and r["storage_type"] else None
            return AgentCustomization(
                agent_id=r["agent_id"],
                provider=provider,
                api_base_url=api_base_url,
                api_key=api_key,
                context_window=context_window,
                tone=r["tone"],
                system_prompt=r["system_prompt"],
                model=r["model"],
                purpose=purpose,
                allowed_tool_names=tools,
                allowed_skill=skills,
                pack_tool_names=pack_tools,
                show_in_chat=show_in_chat,
                max_turns=r["max_turns"],
                history_retention_days=r["history_retention_days"] if "history_retention_days" in r.keys() else None,
                storage_enabled=storage_enabled,
                storage_type=storage_type,
            )
        finally:
            if self._mem_conn is None:
                conn.close()

    def list_agent_overrides(self) -> List[AgentCustomization]:
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT agent_id, provider, api_base_url, api_key, context_window, tone, system_prompt, model, purpose,
                       allowed_tools_json, allowed_skills_json, pack_tools_json, show_in_chat, max_turns, history_retention_days,
                       storage_enabled, storage_type
                FROM agent_overrides
                """
            )
            rows = cur.fetchall()
            results = []
            for r in rows:
                tools = json.loads(r["allowed_tools_json"]) if r["allowed_tools_json"] else None
                skills = None
                if "allowed_skills_json" in r.keys() and r["allowed_skills_json"]:
                    skills = json.loads(r["allowed_skills_json"])
                pack_tools = None
                if "pack_tools_json" in r.keys() and r["pack_tools_json"]:
                    pack_tools = json.loads(r["pack_tools_json"])
                show_in_chat = None
                if "show_in_chat" in r.keys() and r["show_in_chat"] is not None:
                    show_in_chat = bool(r["show_in_chat"])
                purpose = r["purpose"] if "purpose" in r.keys() else None
                provider = r["provider"] if "provider" in r.keys() and r["provider"] else "default"
                api_base_url = r["api_base_url"] if "api_base_url" in r.keys() else None
                api_key = r["api_key"] if "api_key" in r.keys() else None
                context_window = r["context_window"] if "context_window" in r.keys() else None
                storage_enabled = bool(r["storage_enabled"]) if "storage_enabled" in r.keys() and r["storage_enabled"] is not None else None
                storage_type = r["storage_type"] if "storage_type" in r.keys() and r["storage_type"] else None
                results.append(
                    AgentCustomization(
                        agent_id=r["agent_id"],
                        provider=provider,
                        api_base_url=api_base_url,
                        api_key=api_key,
                        context_window=context_window,
                        tone=r["tone"],
                        system_prompt=r["system_prompt"],
                        model=r["model"],
                        purpose=purpose,
                        allowed_tool_names=tools,
                        allowed_skill=skills,
                        pack_tool_names=pack_tools,
                        show_in_chat=show_in_chat,
                        max_turns=r["max_turns"],
                        history_retention_days=r["history_retention_days"] if "history_retention_days" in r.keys() else None,
                        storage_enabled=storage_enabled,
                        storage_type=storage_type,
                    )
                )
            return results
        finally:
            if self._mem_conn is None:
                conn.close()

    def delete_agent_override(self, agent_id: str) -> bool:
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM agent_overrides WHERE agent_id = ?", (agent_id,))
            conn.commit()
            return cur.rowcount > 0
        finally:
            if self._mem_conn is None:
                conn.close()

    def save_agent_profile(self, profile: AgentProfile) -> None:
        now_str = datetime.now(timezone.utc).isoformat()
        tools_json = json.dumps(profile.allowed_tool_names) if profile.allowed_tool_names is not None else None
        skills_json = json.dumps(profile.allowed_skill) if profile.allowed_skill is not None else None
        pack_tools_json = json.dumps(profile.pack_tool_names) if profile.pack_tool_names is not None else None
        show_in_chat = 1 if profile.show_in_chat is not False else 0
        purpose_str = profile.purpose.value if hasattr(profile.purpose, "value") else str(profile.purpose)
        tone_str = profile.tone.value if hasattr(profile.tone, "value") else str(profile.tone)
        created_str = profile.created_at or now_str
        provider_str = getattr(profile, "provider", "default") or "default"

        conn = self._get_connection()
        try:
            conn.execute(
                """
                INSERT INTO custom_agents (
                    id, name, description, system_prompt, provider, api_base_url, api_key, context_window, purpose, tone,
                    avatar_icon, model, allowed_tools_json, allowed_skills_json, pack_tools_json, show_in_chat, max_turns, history_retention_days,
                    is_builtin, storage_enabled, storage_type, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    name = excluded.name,
                    description = excluded.description,
                    system_prompt = excluded.system_prompt,
                    provider = excluded.provider,
                    api_base_url = excluded.api_base_url,
                    api_key = excluded.api_key,
                    context_window = excluded.context_window,
                    purpose = excluded.purpose,
                    tone = excluded.tone,
                    avatar_icon = excluded.avatar_icon,
                    model = excluded.model,
                    allowed_tools_json = excluded.allowed_tools_json,
                    allowed_skills_json = excluded.allowed_skills_json,
                    pack_tools_json = excluded.pack_tools_json,
                    show_in_chat = excluded.show_in_chat,
                    max_turns = excluded.max_turns,
                    history_retention_days = excluded.history_retention_days,
                    is_builtin = excluded.is_builtin,
                    storage_enabled = excluded.storage_enabled,
                    storage_type = excluded.storage_type,
                    updated_at = excluded.updated_at
                """,
                (
                    profile.id,
                    profile.name,
                    profile.description,
                    profile.system_prompt,
                    provider_str,
                    getattr(profile, "api_base_url", None),
                    getattr(profile, "api_key", None),
                    getattr(profile, "context_window", None),
                    purpose_str,
                    tone_str,
                    profile.avatar_icon or "bot",
                    profile.model or "default",
                    tools_json,
                    skills_json,
                    pack_tools_json,
                    show_in_chat,
                    profile.max_turns,
                    profile.history_retention_days,
                    1 if profile.is_builtin else 0,
                    1 if getattr(profile, "storage_enabled", False) else 0,
                    getattr(profile, "storage_type", "sqlite") or "sqlite",
                    created_str,
                    now_str,
                ),
            )
            conn.commit()
        finally:
            if self._mem_conn is None:
                conn.close()

    def get_agent_profile(self, agent_id: str) -> Optional[AgentProfile]:
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT id, name, description, system_prompt, provider, api_base_url, api_key, context_window, purpose, tone,
                       avatar_icon, model, allowed_tools_json, allowed_skills_json, pack_tools_json, show_in_chat, max_turns, history_retention_days,
                       is_builtin, storage_enabled, storage_type, created_at, updated_at
                FROM custom_agents WHERE id = ?
                """,
                (agent_id,),
            )
            r = cur.fetchone()
            if not r:
                return None
            tools = json.loads(r["allowed_tools_json"]) if r["allowed_tools_json"] else []
            skills = []
            if "allowed_skills_json" in r.keys() and r["allowed_skills_json"]:
                skills = json.loads(r["allowed_skills_json"]) or []
            pack_tools = []
            if "pack_tools_json" in r.keys() and r["pack_tools_json"]:
                pack_tools = json.loads(r["pack_tools_json"]) or []
            show_in_chat = True
            if "show_in_chat" in r.keys() and r["show_in_chat"] is not None:
                show_in_chat = bool(r["show_in_chat"])
            provider_val = r["provider"] if "provider" in r.keys() and r["provider"] else "default"
            api_base_url = r["api_base_url"] if "api_base_url" in r.keys() else None
            api_key = r["api_key"] if "api_key" in r.keys() else None
            context_window = r["context_window"] if "context_window" in r.keys() else None
            storage_enabled = bool(r["storage_enabled"]) if "storage_enabled" in r.keys() and r["storage_enabled"] is not None else False
            storage_type = r["storage_type"] if "storage_type" in r.keys() and r["storage_type"] else "sqlite"
            purpose_val = (
                ModelPurpose(r["purpose"]) if r["purpose"] in [p.value for p in ModelPurpose] else ModelPurpose.GENERAL
            )
            tone_val = (
                AgentTone(r["tone"])
                if r["tone"] in [t.value for t in AgentTone]
                else (r["tone"] or AgentTone.DEFAULT)
            )
            return AgentProfile(
                id=r["id"],
                name=r["name"],
                description=r["description"] or "",
                system_prompt=r["system_prompt"],
                provider=provider_val,
                api_base_url=api_base_url,
                api_key=api_key,
                context_window=context_window,
                purpose=purpose_val,
                tone=tone_val,
                avatar_icon=r["avatar_icon"] or "bot",
                model=r["model"] or "default",
                allowed_tool_names=tools,
                allowed_skill=skills,
                pack_tool_names=pack_tools,
                show_in_chat=show_in_chat,
                max_turns=r["max_turns"] or 10,
                history_retention_days=r["history_retention_days"] if r["history_retention_days"] is not None else 30,
                is_builtin=bool(r["is_builtin"]),
                storage_enabled=storage_enabled,
                storage_type=storage_type,
                created_at=r["created_at"],
                updated_at=r["updated_at"],
            )
        finally:
            if self._mem_conn is None:
                conn.close()

    def list_custom_agent_profiles(self) -> List[AgentProfile]:
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT id, name, description, system_prompt, provider, api_base_url, api_key, context_window, purpose, tone,
                       avatar_icon, model, allowed_tools_json, allowed_skills_json, pack_tools_json, show_in_chat, max_turns, history_retention_days,
                       is_builtin, storage_enabled, storage_type, created_at, updated_at
                FROM custom_agents
                ORDER BY created_at ASC
                """
            )
            rows = cur.fetchall()
            results = []
            for r in rows:
                tools = json.loads(r["allowed_tools_json"]) if r["allowed_tools_json"] else []
                skills = []
                if "allowed_skills_json" in r.keys() and r["allowed_skills_json"]:
                    skills = json.loads(r["allowed_skills_json"]) or []
                pack_tools = []
                if "pack_tools_json" in r.keys() and r["pack_tools_json"]:
                    pack_tools = json.loads(r["pack_tools_json"]) or []
                show_in_chat = True
                if "show_in_chat" in r.keys() and r["show_in_chat"] is not None:
                    show_in_chat = bool(r["show_in_chat"])
                provider_val = r["provider"] if "provider" in r.keys() and r["provider"] else "default"
                api_base_url = r["api_base_url"] if "api_base_url" in r.keys() else None
                api_key = r["api_key"] if "api_key" in r.keys() else None
                context_window = r["context_window"] if "context_window" in r.keys() else None
                storage_enabled = bool(r["storage_enabled"]) if "storage_enabled" in r.keys() and r["storage_enabled"] is not None else False
                storage_type = r["storage_type"] if "storage_type" in r.keys() and r["storage_type"] else "sqlite"
                purpose_val = (
                    ModelPurpose(r["purpose"])
                    if r["purpose"] in [p.value for p in ModelPurpose]
                    else ModelPurpose.GENERAL
                )
                tone_val = (
                    AgentTone(r["tone"])
                    if r["tone"] in [t.value for t in AgentTone]
                    else (r["tone"] or AgentTone.DEFAULT)
                )
                results.append(
                    AgentProfile(
                        id=r["id"],
                        name=r["name"],
                        description=r["description"] or "",
                        system_prompt=r["system_prompt"],
                        provider=provider_val,
                        api_base_url=api_base_url,
                        api_key=api_key,
                        context_window=context_window,
                        purpose=purpose_val,
                        tone=tone_val,
                        avatar_icon=r["avatar_icon"] or "bot",
                        model=r["model"] or "default",
                        allowed_tool_names=tools,
                        allowed_skill=skills,
                        pack_tool_names=pack_tools,
                        show_in_chat=show_in_chat,
                        max_turns=r["max_turns"] or 10,
                        history_retention_days=r["history_retention_days"] if r["history_retention_days"] is not None else 30,
                        is_builtin=bool(r["is_builtin"]),
                        storage_enabled=storage_enabled,
                        storage_type=storage_type,
                        created_at=r["created_at"],
                        updated_at=r["updated_at"],
                    )
                )
            return results
        finally:
            if self._mem_conn is None:
                conn.close()

    def delete_agent_profile(self, agent_id: str, purge_history: bool = False) -> bool:
        import shutil
        from pathlib import Path

        from src.application.agent_packs.schema import PLATFORM_PACK_IDS
        from src.domain.agents.profiles import BUILTIN_PROFILES

        builtin_ids = {p.id for p in BUILTIN_PROFILES}
        if agent_id in builtin_ids or agent_id in PLATFORM_PACK_IDS:
            return False

        conn = self._get_connection()
        try:
            cur = conn.cursor()
            # 1. Delete custom agent profile
            cur.execute("DELETE FROM custom_agents WHERE id = ?", (agent_id,))
            deleted = cur.rowcount > 0

            # 2. Always cascade: delete overrides and rebind routines
            try:
                cur.execute("DELETE FROM agent_overrides WHERE agent_id = ?", (agent_id,))
            except Exception:
                pass
            try:
                cur.execute("UPDATE agent_routines SET agent_id = 'assistant' WHERE agent_id = ?", (agent_id,))
            except Exception:
                pass

            # 3. If purge_history=True: clean up all sessions and telemetry
            if purge_history:
                try:
                    cur.execute("DELETE FROM messages WHERE session_id IN (SELECT id FROM chat_sessions WHERE agent_id = ?)", (agent_id,))
                    cur.execute("DELETE FROM chat_sessions WHERE agent_id = ?", (agent_id,))
                except Exception:
                    pass
                try:
                    cur.execute("DELETE FROM telemetry_spans WHERE agent_id = ?", (agent_id,))
                    cur.execute("DELETE FROM agent_turns WHERE agent_id = ?", (agent_id,))
                    cur.execute("DELETE FROM agent_kpis WHERE agent_id = ?", (agent_id,))
                except Exception:
                    pass

            conn.commit()

            # 4. Clean pack directory on disk if present
            try:
                from src.infrastructure.data.resolver import DataDirResolver
                data_dir = DataDirResolver().resolve().root
                pack_folder = Path(data_dir) / "packs" / agent_id
                if pack_folder.is_dir():
                    shutil.rmtree(pack_folder, ignore_errors=True)
            except Exception:
                pass

            return deleted
        finally:
            if self._mem_conn is None:
                conn.close()
