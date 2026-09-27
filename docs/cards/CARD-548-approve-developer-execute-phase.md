---
id: CARD-548
title: "Approve on a Developer Execute phase in an AutoReiv chat resumes and finishes as Developer"
status: In Review
created: 2026-09-27
branch: feat/card-554-553-phase-handoff-tools
related:
  - CARD-544
  - CARD-530
labels:
  - type:bug
  - area:chat
  - P2
---

# [CARD-548] Approving a Developer Execute phase resumes as Developer

> **Status**: In Review on `feat/card-554-553-phase-handoff-tools` (2026-09-27 ET; covered by the CARD-554 + CARD-553 plan). Filed from CARD-544 live QA.
> **Related**: CARD-544, CARD-530
> **Labels**: `type:bug`, `area:chat`, `P2`

## Evidence

CARD-544 made a job phase run as its assigned agent (`profile_for_phase` in `src/web/routers/chat.py`). In live QA a code request to AutoReiv now parks with the Execute phase on Developer, waiting for approval of `execute_code` (desktop and phone). The journey stops at the approval card. Nobody has checked live that Approve resumes the phase as Developer and finishes the job. The resume branch in `chat_stream` streams on the parent session id, not the `::phase::` session. Screenshot: `C:\Users\jacob\AppData\Local\Temp\autoreiv-qa\card-544\card-539-out-of-domain-routing-phone-01-a-code-request-to-autoreiv-goes-to-developer-no-.png`.

## Change

Add a journey step that presses Approve on the `execute_code` card and checks that the job finishes DONE with the reversed string ("vieRotuA") in the reply. Fix the resume path if it runs as AutoReiv or on the wrong session.

## Done when

The approve step passes on desktop and phone, and a unit test covers resume of a phase assigned to another agent.

## Covered by CARD-554 + CARD-553 (2026-09-27)

The CARD-550 journey now covers this card. Its step 2 presses Approve on every approval card in an AutoReiv chat and asserts that the job ends DONE with Developer's Execute phase DONE, a successful `repo_file_read` and a successful `execute_code` or `cli_exec`. It uses the checkout count ask instead of the reversed-string ask.

The resume bug named here was real. The open-job resume path in `chat_stream` streamed the resumed turn on the parent session. After Approve, Developer answered from the parent transcript (in two desktop runs the reply claimed an AST count it never ran), and its phase loop stopped after one tool. Fix: `resume_session_for_phase` resumes in `<sid>::phase::<id>`, and `relay_phase_reply_to_parent` copies the phase's final reply into the chat (`src/web/routers/chat.py`, commit `9712fe7a`). Unit tests are in `tests/unit/orchestration/test_card554_553_phase_handoff_tools.py` (tests `d297ac8a`, red first). Live QA run card-554c passed on desktop and phone. See CARD-554 for the evidence table.
