---
id: CARD-548
title: "Approve on a Developer Execute phase in an AutoReiv chat resumes and finishes as Developer"
status: Ready
created: 2026-09-27
branch: qa
related:
  - CARD-544
  - CARD-530
labels:
  - type:bug
  - area:chat
  - P2
---

# [CARD-548] Approving a Developer Execute phase resumes as Developer

> **Status**: Ready (filed from CARD-544 live QA, 2026-09-27 ~1:45 AM ET).
> **Related**: CARD-544, CARD-530
> **Labels**: `type:bug`, `area:chat`, `P2`

## Evidence

CARD-544 made a job phase run as its assigned agent (`profile_for_phase` in `src/web/routers/chat.py`). In live QA a code request to AutoReiv now parks with the Execute phase on Developer, waiting for approval of `execute_code` (desktop and phone). The journey stops at the approval card. Nobody has checked live that Approve resumes the phase as Developer and finishes the job. The resume branch in `chat_stream` streams on the parent session id, not the `::phase::` session. Screenshot: `C:\Users\jacob\AppData\Local\Temp\autoreiv-qa\card-544\card-539-out-of-domain-routing-phone-01-a-code-request-to-autoreiv-goes-to-developer-no-.png`.

## Change

Add a journey step that presses Approve on the `execute_code` card and checks that the job finishes DONE with the reversed string ("vieRotuA") in the reply. Fix the resume path if it runs as AutoReiv or on the wrong session.

## Done when

The approve step passes on desktop and phone, and a unit test covers resume of a phase assigned to another agent.