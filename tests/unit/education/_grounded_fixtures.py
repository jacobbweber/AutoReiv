"""Shared fixtures for the grounded course step tests [CARD-642..646]."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from src.application.skills.wiki_tools import WikiTools
from src.domain.wiki.store import WikiStore
from src.infrastructure.memory.repositories.agent_memory import AgentMemoryRepository

TOPIC = "Raft log replication"
USER_NOTE = """---
title: Raft log replication
tags: [distributed-systems, raft]
---
# Raft log replication

The leader accepts client commands and appends them to its own log. It sends AppendEntries
messages to every follower. A follower appends the entries only if its log matches the leader's
previous index and term. Once a majority of followers have stored an entry, the leader advances
the commit index and applies the entry to its state machine. Followers learn the commit index
from the next AppendEntries heartbeat. Before replication, a candidate must win an election with
votes from a majority, and terms increase with each election.
"""


class FakeGateway:
    default_model_id = "fake-model"

    def __init__(self, reply=None, error: Exception | None = None):
        self.reply, self.error, self.requests = reply, error, []

    async def complete(self, request):
        self.requests.append(request)
        if self.error:
            raise self.error
        text = self.reply if isinstance(self.reply, str) else "```json\n" + json.dumps(self.reply) + "\n```"
        return SimpleNamespace(text=text)


def make_env(tmp_path: Path):
    repo = AgentMemoryRepository(db_path=tmp_path / "tutor_memory.db")
    repo.initialize_schema()
    wiki_root = tmp_path / "wiki"
    WikiStore(root_dir=wiki_root).scaffold()
    return repo, WikiTools(wiki_root=wiki_root), wiki_root


def add_note(wiki_root: Path, rel: str = "00_Inbox/raft-log-replication.md", text: str = USER_NOTE) -> None:
    p = wiki_root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def md_files(wiki_root: Path) -> set:
    return {str(p.relative_to(wiki_root)) for p in wiki_root.rglob("*.md")}


def mastery(repo) -> list:
    return repo.list_education_mastery(limit=500)
