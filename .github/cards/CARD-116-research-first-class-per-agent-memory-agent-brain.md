# [CARD-116] Research first-class per-agent memory (agent brain)

> **Status**: Ready
> **Created**: 2026-08-30
> **Spec Reference**: docs/specs/per-agent-memory/
> **Labels**: `type:research`, `type:docs`

---

## 1. Why / Intent
Jacob's intent (2026-08-30): each agent needs an **independent brain**, first-class — not one markdown file shared by all agents, and not only Chat session history.

Today AutoReiv has chat transcripts (session persistence plus `history_retention_days`) and a shared episodic fact store (CARD-042, entity/key auto-recall). CARD-114 Finding 22 already notes ACE playbook notes are snapshots, not a second brain. Alignment talks pointed at the same gap: agents do not have their own lasting memory.

**Later talk (2026-08-30 t132u):** Jacob is shying away from LLM-Wiki for this (maintenance). He compared mem0, Letta, and Zep. He wants **what fits AutoReiv intent/vision**. Coding's research leaning is recorded in sections 5-7. It is **not a locked vendor purchase**.

This card is **exploratory research** (what system to build). It is not a coding card and does not lock a vendor.

---

## 2. What to Build
Research only. Do not implement product Python/JS on this card.

- Decide what a first-class per-agent brain is, versus session history and versus a single shared memory file.
- Study Hermes `MEMORY.md` / `USER.md` as **prior art**, not a spec to copy blindly. Hermes research (if referenced): `D:\Projects\research\hermes_research`.
- Agent Studio, per agent: fine-tune controls for how long facts live and other levers, with **hard min/max**.
- Related reading: CARD-114 findings on memory; alignment talks; existing specs `agent-kernel-memory`, `episodic-memory-and-auto-recall`, `agent-session-history-retention` (chat prune is not the brain).
- Record the t132u leaning: three-shelf per-agent brain beside the ReAct kernel; vendor notes (wiki / Letta product / Zep product: no; Mem0: evaluate for archive).
- Short spec stub: `docs/specs/per-agent-memory/requirements.md` (research constraints only).
- CHANGELOG Unreleased note.
- Local commit only. Do not push.

---

## 3. Acceptance Criteria (Definition of Done)
- [ ] Research outcome names what system to build for a first-class per-agent brain. No vendor is locked as the product. Mem0 may be named as the archive engine **to evaluate**.
- [ ] Independent per-agent brain is distinguished from Chat session history and from one markdown file for all agents.
- [ ] Agent Studio per-agent levers (how long facts live and other controls) include hard min/max; later design must honor those bounds.
- [ ] Hermes `MEMORY.md` / `USER.md` studied as prior art, not copied blindly. CARD-114 memory findings and alignment talks are accounted for.
- [ ] Three shelves recorded (pinned / recent summaries / searchable archive). Distinguished from wiki, Letta OS, chat transcripts, CARD-042, ACE notes, and `src/infrastructure/memory` SQLite.
- [ ] Vendor notes recorded (LLM-Wiki no; Letta product no; Zep product no for local-first; Mem0 evaluate for shelf 3). Not a purchase.
- [ ] No product Python/JS. Status stays **Ready** (backlog) until research is accepted. Local commit only. No push.

---

## 4. Constraints & Honor Flags
- Status: **Ready** (backlog). Do not set In Progress.
- Work on `qa`. Do not push. Do not clone.
- Do not implement product code. Do not write Python/JS for the product.
- Do not lock a vendor (vector DB, hosted memory SaaS, LangGraph, Mem0, Letta, Zep, etc.) as the product. Research leaning may name Mem0 as archive engine to evaluate.
- Do not treat Hermes MEMORY.md/USER.md, CARD-042 episodic facts, ACE notes, WikiStore, or Letta as the design.
- Session history retention (`history_retention_days`) is related but is not the agent brain.
- Memory is after skills + tools primitives (CARD-117 / CARD-121). Do not mix this card into those PRs.

---

## 5. Architecture leaning (what to build; vendor is not the system)

Memory = **per-agent brain**, a subsystem beside the existing ReAct kernel. Not a wiki. Not a second agent OS.

- One store per agent id (Coding brain != Okta Admin brain != Sysadmin brain).
- Three shelves AutoReiv owns:
  1. **Pinned** — short block always in the prompt, visible/editable in Agent Studio.
  2. **Recent work summaries** — for that agent.
  3. **Archive** — searchable facts retrieved when relevant.
- Data dir, not git.
- Knobs in Agent Studio with hard min/max (already on this card).

Distinguish from:

| Existing thing | What it is | Not the brain |
| --- | --- | --- |
| Chat transcripts | Session persistence + `history_retention_days` | Conversation log |
| `src/infrastructure/memory` SQLite | Sessions/jobs filing cabinet | Not the brain |
| CARD-042 shared episodic facts | Shared entity/key auto-recall | Shared, not per-agent brain |
| WikiStore / wiki tools | User knowledge | Jacob's notes, not agent brain |
| ACE notes | Playbook snapshots (CARD-114 Finding 22) | Not a second brain |

---

## 6. Vendor evaluation (Aug 2026 research notes — do not lock a purchase)

Source: [Mem0 vs Zep vs Letta, August 2026: The Self-Host Question Just Changed](https://dreaming.press/posts/mem0-vs-zep-vs-letta-self-host-august-2026.html) (Zep Community Edition deprecated Aug 2026). Hermes `MEMORY.md` / `USER.md` remains prior art (`D:\Projects\research\hermes_research`), not a spec.

- **LLM-Wiki: NO for the brain.** Compiled document wiki (pages/links/lint/stale repair). AutoReiv already has WikiStore. Maintenance is the known failure mode Jacob is shying away from. Keep wiki as Jacob's notes.
- **Letta (ex-MemGPT): NO as product.** It is an agent OS (Postgres stateful runtime; the agent lives inside Letta). That fights AutoReiv ReAct / Job / HITL / Ollama. Steal the pin-vs-archive idea only.
- **Zep product: NO for local-first.** Aug 2026 Community Edition deprecated; `getzep/zep` is examples; hosted-only. Graphiti (Apache-2.0 engine) is a later maybe if temporal "true now vs true in March" becomes the pain; needs Neo4j/FalkorDB; too much ops for v1.
- **Mem0: closest bolt-on to EVALUATE for shelf 3** (extract + retrieve beside the existing agent, Apache-2.0, self-host). Must wrap: namespace by `agent_id`, extraction via Ollama not cloud, Agent Studio retention knobs, AutoReiv assembles the prompt. Do not let mem0 own the product. Alternative still open: grow CARD-042 facts into per-agent SQLite + Ollama without mem0.

---

## 7. When we pick this up

Pickup walks with Jacob using **three beats** (what Jacob means, what AutoReiv does now, what we will change). Full working agreement lives on CARD-121 section 7 (and CARD-117 section 6). Confirm the next file/area before editing it.

Memory is **after** skills + tools primitives (CARD-117 then CARD-121), not mixed into those PRs.
