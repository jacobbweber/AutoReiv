---
id: CARD-422
title: "Tools Studio form + Talk/Submit to developer (no code in studio)"
status: Ready
created: 2026-09-22
adr: docs/adr/0057-three-studios-and-developer-mediated-authoring.md
labels:
  - type:feat
  - area:ux
  - area:studios
  - area:tools
  - area:developer
---

# [CARD-422] Tools Studio form + Talk/Submit to developer (no code in studio)

> **Status**: Ready (written in advance so the slice is not forgotten)  
> **Created**: 2026-09-22  
> **ADR Reference**: [ADR-0057](../adr/0057-three-studios-and-developer-mediated-authoring.md)  
> **Depends on**: [CARD-421](./CARD-421-tools-studio-v1-catalog-and-mcp-attach.md) Done (or In Review complete enough that Tools Studio dock exists)  
> **Sibling**: [CARD-423](./CARD-423-custom-tool-packaging-native-and-mcp.md)  
> **Lesson**: [CARD-420](./CARD-420-developer-mediated-authoring-v1-visible-build-review.md) — do not ship Ask developer / Submit until the developer job actually runs with context

---

## Gate language

| Jacob reply | Meaning |
|-------------|---------|
| **`continue`** | Refine AC — **no product code** |
| **`build`** | Implement on `feat/card-422-*` from `qa` after CARD-421 is Done (or he explicitly overrides) |
| **`merge to qa`** | After In Review + live test |

---

## 1. Why / Intent (Beat 1)

Jacob's Tools Studio end state includes create / modify / delete of tools **without the operator typing code**. The studio collects intent on a form (what the tool should do, maybe language or constraints), then **Talk to developer** (open a new developer chat with that form context) and/or **Submit to developer** (start a real mediated job). This card ships that lifecycle only when mediation is real — not a silent queue or theatre button.

---

## 2. What AutoReiv does now (Beat 2)

- After CARD-421: Tools Studio can browse catalog and attach MCP servers.
- Skill Studio had Ask developer removed on CARD-420 because the job did not actually run.
- Authoring / mediation APIs may exist in tree from CARD-420; wire them for **tools** only when the developer path is proven.

---

## 3. What will change (Beat 3)

1. Tools Studio gains a **form** for tool intent (description of behavior, optional language/runtime hints, optional packaging preference pointer to CARD-423 lanes). No code editor.
2. **Talk to developer**: opens a new developer chat prefilled with the form context (and optional paths the operator named in chat fields as plain text, not a folder-picker factory).
3. **Submit to developer**: starts a durable mediated job that the developer actually runs; operator can see status without a fake success.
4. Create / modify / delete flows all go through form + developer; Tools Studio never asks the operator to paste implementation code.
5. Proof: live path from form to developer chat or job; failure modes visible; no theatre.

**Out of scope:** implementing dual native vs MCP packaging rules (CARD-423); MCP hosting UI; Skill Studio skill authoring; typing code in the studio.

---

## 4. What dies (Beat 4)

- Expectation that Tools Studio is a code IDE for tools.
- Expectation that a Submit button that only queues without running the developer is acceptable (CARD-420 lesson).

---

## 5. Acceptance criteria (EARS)

- **[REQ-422-001]** WHEN the operator fills the Tools Studio tool form and chooses **Talk to developer**, THE SYSTEM SHALL open a developer chat that includes the form context and SHALL NOT require the operator to retype that context.
- **[REQ-422-002]** WHEN the operator chooses **Submit to developer**, THE SYSTEM SHALL start a real developer-mediated job (or refuse clearly if mediation is unavailable) and SHALL NOT report success for a no-op queue.
- **[REQ-422-003]** THE SYSTEM SHALL NOT present a code editor or require the operator to paste tool implementation code inside Tools Studio.
- **[REQ-422-004]** WHEN create, modify, or delete is requested from Tools Studio, THE SYSTEM SHALL route the intent through the form + developer path above.

---

## 6. Verification

Manual live test after build:

1. Open Tools Studio, open create/modify form, fill intent, Talk to developer — new chat has context.
2. Submit to developer — job runs or clear failure; no silent success.
3. Confirm no code editor in the studio.

---

## 7. Honest scope note

This card is Ready before CARD-421 ships so Jacob always sees the next Tools Studio slice. Do not **build** until CARD-421 is Done unless he explicitly says otherwise.
