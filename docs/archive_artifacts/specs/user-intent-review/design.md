# Design: User Intent Review and Product Alignment

> **Spec Status**: Approved (review artifact)
> **Companion**: findings.md is the payload. This file only says how the review was done.

---

## Method
Read and grep current qa (not only the chat recap):

- Kernel: stream_turn vs 
un_turn, nested caps, DONE when no tool calls
- Planner: 	ools=None, leftover DAG comments, leftover /api/chat/goal
- Chat: Goal/Verify flags, every chat creates a job, abort route
- HITL: /api/approvals vs leftover /api/hitl
- Handoff packet + semaphore vs parallel worker
- Forge / Agent Builder / propose_skill / commit_skill_pack
- User packs, Okta seed stubs, Skills Studio
- ACE online + paused skill-eval / curator
- Data dir vs checkout ./data, wiki path, launcher
- SDLC Conductor/Coding/Review vs Job/Phase
- CARD board statuses 001–113

No product files were changed except this spec, CARD-114, and CHANGELOG.

---

## How findings are used
Jacob talks. Grok maps what he says onto a finding number and the live code. If they disagree, the finding is wrong or stale — update it, do not sneak a fix.
