# [CARD-116] Research first-class per-agent memory (agent brain)

> **Status**: Ready
> **Created**: 2026-08-30
> **Spec Reference**: docs/specs/per-agent-memory/
> **Labels**: `type:research`, `type:docs`

---

## 1. Why / Intent

**Do not pick this card up yet.** Pickup is blocked until AFTER both of these:

1. Walking the **other pile** (orchestration / Goal / loops / graphs and related parked alignment).
2. The open **foundation refactor** cards: CARD-117 skills, CARD-121 tools, CARD-120 Python skill rename, CARD-118 studio freeze. CARD-119 Agent Packs stays later-discuss.

Memory is a **bolt-on after those are ironed out**. Timing is confirmed correct: subsystem beside ReAct, not a parallel epic now. Later-us must not start CARD-116 early.

Jacob's intent (2026-08-30): each agent needs an **independent brain**, first-class — not one markdown file shared by all agents, and not only Chat session history.

Today AutoReiv has chat transcripts (session persistence plus `history_retention_days`) and a shared episodic fact store (CARD-042, entity/key auto-recall). CARD-114 Finding 22 already notes ACE playbook notes are snapshots, not a second brain. Alignment talks pointed at the same gap: agents do not have their own lasting memory.

**Later talk (2026-08-30 t132u):** Jacob is shying away from LLM-Wiki for this (maintenance). He compared mem0, Letta, and Zep. He wants **what fits AutoReiv intent/vision**. Coding's research leaning is recorded in sections 5-7. It is **not a locked vendor purchase**.

**Later talk (2026-08-30 t133u):** Explore **both** Mem0 **and** a native/better-fit alternative (grow CARD-042 per-agent SQLite+Ollama, or whatever research shows is better). Do **not** lock Mem0. When this card is later executed: **START with Mem0 deep research** so we truly understand it, **THEN** compare with what could be a better potential fit.

This card is **exploratory research** (what system to build). It is not a coding card and does not lock a vendor.

---

## 2. What to Build
Research only. Do not implement product Python/JS on this card.

- Decide what a first-class per-agent brain is, versus session history and versus a single shared memory file.
- Prior art studied outside this repo, not a spec to copy blindly.
- Agent Studio, per agent: fine-tune controls for how long facts live and other levers, with **hard min/max**.
- Related reading: CARD-114 findings on memory; alignment talks; existing specs `agent-kernel-memory`, `episodic-memory-and-auto-recall`, `agent-session-history-retention` (chat prune is not the brain).
- Record the t132u leaning: three-shelf per-agent brain beside the ReAct kernel; vendor notes (wiki / Letta product / Zep product: no).
- Record the t133u research order: **Mem0 deep research first**, then compare a native/better-fit alternative (grow CARD-042 per-agent SQLite+Ollama, or whatever research shows is better). Do not lock Mem0.
- Short spec stub: `docs/specs/per-agent-memory/requirements.md` (research constraints only).
- CHANGELOG Unreleased note.
- Local commit only. Do not push.

---

## 3. Acceptance Criteria (Definition of Done)
- [ ] Research outcome names what system to build for a first-class per-agent brain. No vendor is locked as the product. Explore **both** Mem0 **and** a native/better-fit alternative. Do not lock Mem0.
- [ ] When later executed: Mem0 is researched **first** (deep enough that we truly understand it), **then** compared with the native/better-fit alternative (grow CARD-042 per-agent SQLite+Ollama, or whatever research shows is better).
- [ ] Independent per-agent brain is distinguished from Chat session history and from one markdown file for all agents.
- [ ] Agent Studio per-agent levers (how long facts live and other controls) include hard min/max; later design must honor those bounds.
- [ ] Prior art outside this repo studied, not copied blindly. CARD-114 memory findings and alignment talks are accounted for.
- [ ] Three shelves recorded (pinned / recent summaries / searchable archive). Distinguished from wiki, Letta OS, chat transcripts, CARD-042, ACE notes, and `src/infrastructure/memory` SQLite.
- [ ] Vendor notes recorded (LLM-Wiki no; Letta product no; Zep product no for local-first). Mem0 is a research candidate, not a purchase.
- [ ] Pickup order is explicit: do not start until after the other pile (orchestration / Goal / loops / graphs) and foundation refactor cards (CARD-117, CARD-121, CARD-120, CARD-118). CARD-119 stays later-discuss.
- [ ] No product Python/JS. Status stays **Ready** (backlog) until research is accepted. Local commit only. No push.

---

## 4. Constraints & Honor Flags
- **Pickup blocked.** Do not start CARD-116 until AFTER (a) walking the other pile (orchestration / Goal / loops / graphs and related parked alignment) and (b) the open foundation refactor cards (CARD-117 skills, CARD-121 tools, CARD-120 Python skill rename, CARD-118 studio freeze). CARD-119 Agent Packs stays later-discuss. Memory is a bolt-on after those are ironed out. Not a parallel epic now.
- Status: **Ready** (backlog). Do not set In Progress.
- Work on `qa`. Do not push. Do not clone.
- Do not implement product code. Do not write Python/JS for the product.
- Do not lock a vendor (vector DB, hosted memory SaaS, LangGraph, Mem0, Letta, Zep, etc.) as the product. Explore both Mem0 and a native/better-fit alternative. Do not lock Mem0.
- When later executed: START with Mem0 deep research, THEN compare with native/better-fit.
- Do not treat prior-art memory layouts, CARD-042 episodic facts, ACE notes, WikiStore, or Letta as the design.
- Session history retention (`history_retention_days`) is related but is not the agent brain.
- Keep three-shelf architecture. Wiki / Letta product / Zep product stay out.

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

Source: [Mem0 vs Zep vs Letta, August 2026: The Self-Host Question Just Changed](https://dreaming.press/posts/mem0-vs-zep-vs-letta-self-host-august-2026.html) (Zep Community Edition deprecated Aug 2026). Prior art studied outside this repo, not a spec.

- **LLM-Wiki: NO for the brain.** Compiled document wiki (pages/links/lint/stale repair). AutoReiv already has WikiStore. Maintenance is the known failure mode Jacob is shying away from. Keep wiki as Jacob's notes.
- **Letta (ex-MemGPT): NO as product.** It is an agent OS (Postgres stateful runtime; the agent lives inside Letta). That fights AutoReiv ReAct / Job / HITL / Ollama. Steal the pin-vs-archive idea only.
- **Zep product: NO for local-first.** Aug 2026 Community Edition deprecated; `getzep/zep` is examples; hosted-only. Graphiti (Apache-2.0 engine) is a later maybe if temporal "true now vs true in March" becomes the pain; needs Neo4j/FalkorDB; too much ops for v1.
- **Mem0: research first, do not lock.** Closest named bolt-on for shelf 3 (extract + retrieve beside the existing agent, Apache-2.0, self-host). When this card is later executed, **START with Mem0 deep research** so we truly understand it. Must wrap if used: namespace by `agent_id`, extraction via Ollama not cloud, Agent Studio retention knobs, AutoReiv assembles the prompt. Do not let mem0 own the product.
- **Then compare a native/better-fit alternative.** Grow CARD-042 per-agent SQLite + Ollama without mem0, or whatever research shows is better. Explore **both**. Do not lock Mem0.

---

## 7. When we pick this up

**Do not pick this card up yet.** Explicit order so later-us cannot start 116 early:

1. Walk the **other pile** first (orchestration / Goal / loops / graphs and related parked alignment).
2. Then the open **foundation refactor** cards: CARD-117 skills, CARD-121 tools, CARD-120 Python skill rename, CARD-118 studio freeze. CARD-119 Agent Packs stays later-discuss.
3. Memory is a **bolt-on after those are ironed out**. Timing is confirmed: subsystem beside ReAct, not a parallel epic now.

When this card is later executed:

- START with **Mem0 deep research** so we truly understand it, THEN compare with a native/better-fit alternative (grow CARD-042 per-agent SQLite+Ollama, or whatever research shows is better). Do not lock Mem0.
- Pickup walks with Jacob using **three beats** (what Jacob means, what AutoReiv does now, what we will change). Full working agreement lives on CARD-121 section 7 (and CARD-117 section 6). Confirm the next file/area before editing it.
