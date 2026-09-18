# [CARD-352] In-Situ Skill Workshop: /learn Distillation from Chat

> **Status**: In Review  
> **Created**: 2026-09-17  
> **Spec Reference**: `docs/specs/in-situ-skill-distillation/`, `docs/adr/0052-skill-and-tool-scoping-and-specialist-dispatch.md`, Nous Hermes `/learn`, SkillOpt  
> **Labels**: `type:feature`, `AutoReiv.Web`, `AutoReiv.Chat`, `domain:skills`, `domain:learning`  

---

## 1. Locked Decisions (Human Visionary Alignment)

Decisions locked with Jacob on 2026-09-18:
1. **Trigger Affordance**: Buttons over manual typing. Primary trigger is a prominent `[ 💡 Teach Agent ]` icon button on assistant message headers in Chat Studio. Clicking opens a lightweight modal that auto-diagnoses the turn context with an optional correction prompt. Optional `/learn` shortcut remains supported in chat composer.
2. **Review & Adoption Card**: Inline interactive **Skill Proposal Card** directly in the chat stream. Explains the issue and remedy in plain language up front with an expandable Markdown preview accordion, followed by one-click `[ ✅ Adopt Skill ]`, `[ ✏️ Quick Tweak ]`, and `[ ✕ Dismiss ]` actions.
3. **Escalation to Factory**: When distillation detects that the capability requires a new native Python tool (rather than procedural rules), the card clearly explains the need and provides a prominent `[ 🚀 Send to Factory Studio ]` button pre-filling Target Agent, Intent, and Objectives into Factory Studio's intake workbench.

---

## 2. Three Beats

### Beat 1: What Jacob means
Most day-to-day agent capability gaps do not require compiling new Python tools in an 8-phase code factory. When an agent makes a procedural error during a chat (such as saving a wiki template to `notes/resources/` instead of `resources/templates/`), the operator needs to be able to correct and teach the agent in-situ. AutoReiv must provide a fast learning loop (similar to Hermes `/learn` or SkillOpt) that takes the conversation transcript, the failed action, and the operator's correction, distilling them into a standardized, staged `SKILL.md` runbook in seconds.

### Beat 2: What AutoReiv does now
* AutoReiv has no in-situ self-learning or procedural distillation loop.
* If an agent fails in Chat, the operator must either manually create a directory and write a raw `SKILL.md` file by hand, or leave Chat, navigate to Factory Studio, and run an 8-phase code compiler that was designed for synthesizing Python tools, not runbooks.

### Beat 3: What will change
1. **Chat Studio Trigger (`chat.js`, `templates/index.html`)**:
   * Add a `[ 💡 Teach Agent ]` icon button to assistant message headers in Chat Studio.
   * Support entering `/learn [optional steering guidance]` in the chat prompt box.
2. **Backend Distillation Endpoint (`POST /api/skills/distill`)**:
   * Captures the recent conversation trajectory (user prompt, agent tool calls, errors, human correction).
   * Runs a fast, structured LLM distillation pass enforcing strict authoring standards:
     * YAML frontmatter: `name`, `description` (<60 chars), and relevant `tools`.
     * Sections: `## When to Use`, `## Procedure`, `## Common Pitfalls & Forbidden Paths`, `## Verification`.
   * Checks for tool capability: If existing tools are sufficient, it drafts the runbook. If a new native tool is needed, it generates an escalation payload for Factory Studio.
3. **Staged Skill Review & One-Click Adoption**:
   * Renders an interactive **Skill Proposal Card** directly in the chat stream.
   * The operator can inspect the proposed runbook text, make quick manual edits, or click `[ ✅ Adopt Skill to <Agent> ]`.
   * Upon adoption, the file is saved to `packs/<agent_id>/skills/<slug>/SKILL.md`, registered in the agent manifest, and is active for the very next turn.

---

## 3. Acceptance Criteria (Definition of Done)

- [ ] Chat Studio supports `/learn` command and `[ 💡 Teach Agent ]` message action.
- [ ] Backend endpoint `POST /api/skills/distill` extracts turn context and synthesizes valid `SKILL.md`.
- [ ] Generated runbook strictly adheres to authoring rubrics (<60 char description, procedural steps, pitfalls, verification).
- [ ] Chat renders an inline proposal card with Markdown preview and `[ ✅ Adopt Skill ]` button.
- [ ] Clicking Adopt writes the file to the agent's user-data pack and mounts it immediately.
- [ ] If new native code tools are required, the proposal card includes an "Escalate to Factory Studio" bridge.
- [ ] Comprehensive automated tests cover distillation endpoint and adoption persistence.
- [ ] Zero lint errors via `ruff check .` and `npm run lint:frontend`.

---

## 4. Constraints & Honor Flags
- Skills must be saved strictly under user data packs (`packs/<agent_id>/skills/`), never under git checkout.
- No code without Jacob's explicit `build` instruction.
