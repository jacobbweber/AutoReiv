---
id: CARD-422
title: "Tools Studio form + Talk/Submit to developer (no code in studio)"
status: In Review
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

> **Status**: In Review  
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

CARD-421 is on `qa`. This slice is In Review. CARD-423 stays Ready. Packaging preference on the form is a note for the developer. This card does not build native or MCP runtime lanes.

## 8. What shipped

- Form in Tools Studio: intent (create / modify / delete), tool name, what the tool should do, optional language hint, runtime hint, plain-text path, packaging note. Catalog **Modify** and **Delete intent** fill that form. They do not paste code and they do not delete a catalog row by themselves.
- **Talk to developer** `POST /api/tools_studio/authoring/talk` creates a new `developer` session and saves the form as the first user message. The studio then opens that chat. It does not mint a job and it does not call the model.
- **Submit to developer** `POST /api/tools_studio/authoring/jobs` creates a standing job (`tools_studio_developer_mediation`), starts the author phase, and calls `kernel.run_turn` on that same developer session. Success is HTTP 200 only when the turn returns a non-empty reply and the job is no longer `queued` (`done`, or `waiting_approval` if a confirmation is pending). Missing kernel, a raised turn, an empty reply, or a timeout returns HTTP 503 with `ran: false` and closes the job as `failed` or `cancelled`.
- Timeout uses the standing phase limit (`STANDING_PHASE_LLM_TIMEOUT_SECONDS`, default 300). The request waits for that turn.
- The reply is the developer’s answer in chat. This form does not write a tool file and does not apply native or MCP packaging.

### Proof

- `tests/integration/operator_contracts/test_oc422_tools_studio_developer_mediation.py`
- `tests/unit/frontend/card_422_tools_studio_authoring.test.js`

### Live test

1. Open Tools Studio. Confirm the intent form is on the page and there is no code editor. Catalog search, MCP attach, and disable still work.
2. Fill **What the tool should do**, choose **Talk to developer**. Chat opens on the developer agent in a new session, and the first message already contains the form text.
3. Submit the same kind of intent. The status line shows a job id and a developer reply, or a clear error. A spinner that ends with no job and no error is a failure of this card.
4. A packaging note of native or MCP does not create a package.
