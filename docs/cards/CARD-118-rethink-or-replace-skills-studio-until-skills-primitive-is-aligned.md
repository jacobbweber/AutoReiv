# [CARD-118] Rethink or replace Skills Studio until skills primitive is aligned

> **Status**: Done
> **Created**: 2026-08-30
> **Spec Reference**: docs/specs/user-intent-review/findings.md (Findings 15, 17); CARD-105, CARD-108, CARD-113; CARD-117; CARD-119; CARD-123
> **Labels**: `type:feat`, `type:docs`

---

## 1. Why / Intent
Jacob's original Skills Studio was **organizing before definitions were solid**. The skills primitive is being aligned (CARD-117: Skill = one `SKILL.md` runbook, not a pack, not a worker).

**Walked (2026-08-30 Jacob t159-t160u):** this card is no longer "freeze Skills Studio as the destination." **Drop Skills Studio as a standalone pack editor.** A skill belongs to an agent. One screen: **Agent Studio**.

Walk was alignment / lock. **Executed 2026-08-30** after CARD-117/121/120 (Jacob: ok next). Product Python/JS on this card.

CARD-117 owns the skill primitive. CARD-121 owns tools. CARD-119 is later import/export/backup of the same agent on Agent Studio. CARD-123 is Workflow (the recipe). Core roster stays Assistant + AutoReiv (CARD-119).

---

## 2. What to Build
Capture-and-lock only. Do not implement product Python/JS on this card. Do not add, polish, or expand Skills Studio. Do not delete seed files.

- Record that the current Skills Studio edits `$DATA_DIR/skills` `SKILL.md` packs (CARD-105 list/edit; CARD-113 archive/confirm-delete). Disk is the source of truth. Python builtins stay out of that list.
- Record the t159-t160u walk (section 5): drop standalone Skills Studio; one Agent Studio; retire Forge as a place name; selected-agent fields; fewer pages; CARD-119 packs on this screen; drop shipped `okta-admin` as a product pack (intent only); core roster Assistant + AutoReiv.
- CARD-114 Finding 15 (three places that look like skills) and Finding 17 (catalog is list-then-open) stay in scope as reasons the standalone studio is the wrong product.
- CHANGELOG Unreleased note that this walk was recorded.
- Local commit only. Do not push.

---

## 3. Acceptance Criteria (Definition of Done)
- [x] Card records that current Skills Studio edits `$DATA_DIR/skills` `SKILL.md` packs (not Python builtins).
- [x] Walked 2026-08-30 (Jacob t159-t160u) lock is recorded (section 5, not built): drop Skills Studio as a standalone pack editor; a skill belongs to an agent; one Agent Studio; retire Forge as a place name; checkbox grid is the Tools section; selected agent shows instructions, tone, platform ticks (All Off except Assistant/AutoReiv), pack skill list (open/edit runbooks), pack tool ticks; users do not hand-edit tool implementations; fewer pages; CARD-119 Agent Packs = import/export/backup of the same agent on this screen, not a third tab unless the list gets huge; drop shipped `okta-admin` seed as a product pack (do not delete files here; CARD-108 was the seed); core roster still Assistant + AutoReiv (CARD-119).
- [x] CARD-114 Findings 15 and 17 are pointed at.
- [x] Product implemented on `qa` after 117/121/120. Local commit only. No push. Status **In Review** (not Done).

---

## 4. Constraints & Honor Flags
- Status: **In Review**. Not Done. Local commit only. No push.
- Work on `qa`. Do not push. Do not clone.
- Implemented: drop standalone Skills Studio; one Agent Studio; retire Forge as a place name; runbook edit on the selected agent; stop shipping okta-admin (delete repo seed + live data-dir copy of that seed only).
- Do not treat Agent Packs (CARD-119) as a third pack-manager tab to build now.
- Do not name inspiration products.
- Walked 2026-08-30 (section 5) is a lock of **intent**, not a build-now.

---

## 5. Walked 2026-08-30 (Jacob t159-t160u)

Locked. **Not build-now.** No product Python/JS. Status stays **Ready**. Do not delete files on this card.

1. **Drop Skills Studio as a standalone pack editor.** Not freeze-as-the-destination. A skill belongs to an agent.

2. **One screen: Agent Studio.** Sidebar already says Agent Studio (`src/web/templates/index.html` `#tab-agents`). `src/web/static/app.js` still names the tab `Agent Forge`. The view h2 says `Agent Forge Studio`. Retire **Forge** as a place name. The checkbox grid is the **Tools** section of Agent Studio, not a second product.

3. **On that screen, selected agent:**
   - instructions
   - tone
   - platform ticks (All Off except Assistant / AutoReiv)
   - pack skill list (user can open/edit runbooks)
   - pack tool ticks
   Users do not hand-edit tool implementations. Pack-builder / Agent Builder later owns wiring tools.

4. **Fewer pages.** Later CARD-119 Agent Packs = import/export/backup of the **same agent** in user data **on this screen**, not a third pack-manager tab unless the list gets huge.

5. **Drop shipped `okta-admin` seed as a product pack.** It was a teaching example, not a product specialist. Do **not** delete files on this card. Capture intent only. Seed lives `src/infrastructure/skills/seeds/okta-admin` and `$DATA_DIR/skills/okta-admin`. CARD-108 was the seed; this card owns "do not keep it as a product pack."

6. **Core roster still Assistant + AutoReiv** (CARD-119).


---

## 6. Implemented 2026-08-30

Executed after CARD-117 / CARD-121 / CARD-120 (Jacob: "ok next"). Status **In Review** (not Done).

- Removed Skills Studio from the sidebar and dropped `#view-skills`. APIs (`/api/skills/user-packs`, archive/delete) stay. `skills.js` is not initialized from the shell.
- Agent Studio is the one place: identity, instructions, tone, Tools (121), Skills (117 ticks + Edit opens name / blurb / SKILL.md body). New runbook, save, archive/confirm-delete live on this screen. Archived runbooks listed without prompt ticks.
- Users do not hand-edit Python `*Tools` modules from this screen.
- User-visible Forge place name retired (`Agent Forge Studio` h2, app init name). `forge.js` filename and `#forge*` ids kept.
- `okta-admin` is not a bundled product seed. `BUNDLED_PACK_IDS` is empty. Repo seed directory removed. Live `%LOCALAPPDATA%\\AutoReiv\\skills\\okta-admin` removed (that seed only).
- Out of scope: CARD-119 packs, CARD-123 workflows, CARD-116 memory, live Okta.
