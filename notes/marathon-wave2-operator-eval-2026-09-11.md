# Wave-2 operator eval pack (asks 1–4) — live evidence

**Date**: 2026-09-11 (America/New_York)  
**Branch tip**: `grok` @ `171364e` (CARD-235 merged)  
**Serve**: `http://127.0.0.1:8000` · model `qwen3.8:latest` @ `192.168.1.29:11434`  
**Live data dir** (not repo `data/`): `C:\Users\jacob\AppData\Local\AutoReiv\`  
**DB**: `C:\Users\jacob\AppData\Local\AutoReiv\database\autoreiv.db`  
**Chat session**: `44bf694d-ee1c-4726-954a-658e543a3b35` (title: weather metaphor → full walk)  
**Jacob decision**: **pass wave 2** (operator UI felt good)

CoS looked at repo `D:\Projects\Active\AutoReiv\data\` earlier — that folder is **not** the live serve root. Live sessions/wiki land under `%LOCALAPPDATA%\AutoReiv\`.

---

## Ask results (operator UI + API)

| Ask | Expect | Operator | Builder evidence | Standing Job/`job_id` |
|-----|--------|----------|------------------|------------------------|
| **1** Short chitchat | Plain ReAct, no Job | PASS | User: weather metaphor → one-sentence control-plane reply; no tools | PASS — no Job strip / `journey.jobs=[]` |
| **2** Outcome Wiki note | Job + `success_rule` + matched IDs + Observe journey | PASS (note exists) | Note created + curated to `01_Notes/information_technology/agent_platform/what_is_a_job_in_autoreiv.md` (uid `20260911-102304`); `wiki_note_create` HITL then read-back | **GAP** — Chat journey `total_jobs: 0`; no Job row for this session in live DB |
| **3** Thin/gap research | Research span or explicit skip | PASS (felt grounded) | Listed tools/packs; `skill_view` proposals + wiki; plan with “invent nothing trusted” | **GAP** — no `standing.research` / Job checkpoint for this session |
| **4** Fail health `:9` | Verify fail → replan≤3 or honest park | PASS (honest fail) | Handoff to `autoreiv` child `…_child_9659458e`; `cli_exec` exit 28, STATUS:000, ~1s timeout; assistant reported FAILED | **GAP** — handoff Job/tool path, not standing verifier replan/park spans for a parent Job |

---

## Artifacts

- **Wiki note (ask 2)**: `C:\Users\jacob\AppData\Local\AutoReiv\wiki\01_Notes\information_technology\agent_platform\what_is_a_job_in_autoreiv.md` (also searchable via `/api/wiki/search?q=Job`)
- **Session API**: `/api/sessions/44bf694d-ee1c-4726-954a-658e543a3b35/messages` (21 msgs)
- **Chat journey API**: `/api/chat/sessions/44bf694d-ee1c-4726-954a-658e543a3b35/journey` → tools ok, **jobs empty**
- **Child handoff (ask 4)**: `44bf694d-ee1c-4726-954a-658e543a3b35_child_9659458e`

---

## Honest bar vs Architect P0 gate

Jacob’s **pass wave 2** stands for operator trust.  

Builder gate note: asks **2–4 succeeded as capable Chat/ReAct (+ handoff)**, but did **not** prove the standing Job spine in Observability (`job_id` journey with intake / research-or-skip / verify-replan). Likely causes to chase as follow-up (not blocking Jacob’s feature pitch):

1. Outcome-intake classifier did not promote these prompts into durable Jobs on the live Chat path Jacob used.
2. Serve may still be a mix of behaviours vs unit smoke paths (restart after `171364e` assumed).
3. Document live data root in runbook: `%LOCALAPPDATA%\AutoReiv\` (P0 #2 serve/restart runbook).

**Recommended follow-ups (do not reopen wave 2):**
- P1: one forced Chat ask that **must** create a Job + show Observe `job_id` (intake proof).
- P1: Forge approve → Job resume E2E (already queued).
- P0 runbook: “live data = AppData Local AutoReiv; restart serve after pull.”

---

## Status

- Operator: **pass wave 2** (Jacob)
- Eval pack 1–4 operator outcomes: **PASS**
- Eval pack standing Job/`job_id` proof for 2–4: **NOT YET** (tracked gap, not a rollback)
