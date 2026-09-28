---
id: CARD-470
title: "Chat Auto-run toggle is inverted since the CARD-397 split: unchecked means tools run without asking"
status: Done
created: 2026-09-24
updated: 2026-09-24
branch: feat/card-470-auto-run-toggle-fix
related:
  - CARD-397
  - CARD-469
  - REQ-HITL-028
  - REQ-TOOLPOL-003
labels:
  - type:bug
  - area:chat
  - area:hitl
  - area:frontend
  - P0
---

# [CARD-470] Chat Auto-run toggle is inverted since the CARD-397 split: unchecked means tools run without asking

> **Status**: Done (Jacob live-tested round 2 and said `merge to qa`, 2026-09-25 12:44 AM ET)
> **Created**: 2026-09-24
> **Observed during**: CARD-469 planning. `git blame` puts the broken line on `7b563003` (CARD-397, 2026-09-20 11:06 PM ET).
> **Verified live-safely (2026-09-24 ~11:45 PM ET, qa `ae9c0a18`)**: on the scratch smoke server (`scripts/smoke_server.py --port 8766`, data wiped under `scratch/smoke_data`, never live AppData), with a fake tool-calling LLM and a Playwright probe that intercepted `/api/chat/stream`. The results are in section 1, Beat 2.
> **Related**: CARD-397, CARD-469, REQ-HITL-028, REQ-TOOLPOL-003
> **Labels**: `type:bug`, `area:chat`, `area:hitl`, `area:frontend`, `P0`

---

## Gate language (exact reply phrases)

| Jacob reply | Meaning |
|-------------|---------|
| **`continue`** | Refine. **Still no product code** |
| **`build`** | Fix test-first |
| **`merge to qa`** | After In Review and the runbook passes on Jarvis |

Do not write product code until Jacob says **build** on this card.

---

## 1. Four Beats

### Beat 1: What Jacob means

With Auto-run **off**, AutoReiv must stop and ask before any tool that needs approval (writes, shell, code execution, git, card or spec edits). With it **on**, those tools run without asking. Blocked tools stay blocked either way. The choice should be remembered across reloads, and the chips next to the composer should show which modes are on.

### Beat 2: What AutoReiv does now (qa `ae9c0a18`, verified)

1. **The flag is inverted (verified live).**
   - `src/web/static/modules/studios/chat.js` L816: `approvalAutoRun: approvalToggle ? !approvalToggle.checked : false`.
   - `src/web/static/modules/studios/chat/stream.js` L31: `approval_mode: approvalAutoRun ? 'run' : 'ask'`.
   - Playwright probe, fresh browser:
     - Auto-run unchecked (the default) sent **`approval_mode: "run"`**.
     - Auto-run checked sent **`"ask"`**.
     - With a saved preference of `autoreiv_approval_autorun='run'`, the toggle still loaded unchecked and sent `"run"`.
   - Self-Verify is **not** inverted: L815 sends `self_verify: verifyToggle.checked`.
   - Before the split (`7b563003^` chat.js): L3157 sent `state.approvalAutoRun`, and the change handler at L2194-2197 set it from `checked`. That was correct.
2. **What `run` does on the backend (verified live).**
   - `src/application/safety/tool_policy_gate.py` L558-562: any `REQUIRE_CONFIRM` verdict returns `None` (allowed) when mode is `run`. Otherwise it parks the call through `hitl_engine.park_tool_call`. Anything other than `"run"` counts as `ask`, including `"auto"` from `mcp_server.py` L221.
   - Scratch probe with agent `autoreiv` and the tool `wiki_note_create`:
     - `ask` sent SSE `approval_required` (`appr_99ffb57868ad`, "Parked for operator approval... The tool was not executed"), and no note file was written.
     - `run` sent no approval event. `tool_output` returned `success: true`, and the note was written to `scratch/smoke_data/wiki/00_Inbox/card_470_probe.md`. The model then got a second turn with the tool result.
   - Tools that `run` lets through without asking:
     - `_DEFAULT_REQUIRE_CONFIRM` (L26-47): `cli_exec`, `execute_code`, `wiki_note_create`/`_update`/`_organize`, `write_card`, `write_spec`, `set_card_status`, `write_project_file`, `create_project`, `git_commit`, `sync_card_issue`, `execute_agent_database`, `repo_file_write`/`_patch`/`_rollback`, `repo_create_worktree`/`repo_remove_worktree`.
     - MCP tools whose names look dangerous (write/delete/exec/shell/run/create/update…, L281-317 and L424-435).
     - Anything listed in `settings.require_confirm_tools` (L437-449).
     - Skill proposals: `skill_proposals.py` L491-508 (also reached through `agent_builder_tools.py` L343) parks a draft in `ask` mode and writes it directly in `run` mode.
   - What still applies in `run` mode (`BLOCK` verdicts):
     - the agent tool allowlist (L385-395)
     - the capability subset
     - `DangerousCommandFilter` for `cli_exec` (L411-422)
     - `block_tools`
   - There is **no separate per-agent approval setting** that would catch these. `hitl_engine.requires_approval` (`src/application/kernel/hitl_engine.py` L46) is never called, so the gate is the only approval layer. Kernel call site: `agent_kernel.py` L1150-1168. The mode is also passed into the tool context at `tool_registry.py` L188.
3. **The inverted value spreads.**
   - `src/web/routers/chat.py` passes `req.approval_mode` into the kernel, job-graph and handoff paths (L1939, L2050, L2077, L2267, L2279).
   - Resume uses `stored_mode or req.approval_mode` (L1894).
   - Jobs read it from plan args (L366).
   - `handoff_engine.py` L354/531/553 copy the parent's mode into child envelopes (REQ-HITL-028, `models.py` L45).
   - So any chat started since 2026-09-20 with Auto-run unchecked ran its jobs and child agents in `run` mode too.
4. **Other surfaces checked. None of them are inverted.**
   - Routines: `routines.js` L313/L536 map checked to `run`, and the backend (`routines.py` L65/94/138, `executor.py` L432) normalizes correctly.
   - HITL resume paths (`hitl.py`) hard-code `ask`.
   - Hosted MCP server: `"auto"`, which counts as `ask`.
   - `native_tools.py` defaults to `ask`.
   - **Education** (`education.js` L972) sends `state.approvalAutoRun`. Nothing sets that since the split (`store.js` L46 defaults it to `false`), so Education always sends `ask` and ignores the toggle. That is safe, but stale. `education.js` L1896 leaves the field out, so it also defaults to `ask`.
5. **The saved choice is lost.** Pre-split L2190-2200 restored the toggle with `readLastApprovalAutoRun()` and saved it with `writeLastApprovalAutoRun()`. Both still exist in `chat/hitl.js` L164/L173 (key `autoreiv_approval_autorun`, value `'run'`/`'ask'`, fails safe to `ask`), but nothing calls them. Browsers that saved `'run'` before 2026-09-20 still have it stored.
6. **The chips are dead (verified live).** There are no `change` listeners on `#verifyToggle` or `#approvalToggle` any more. The pre-split listeners were at L2183-2199. After checking both toggles, `#verifyBadge` and `#approvalBadge` (index.html L563/L566) stayed hidden. `state.verifyEnabled` is also no longer updated from the toggle.
7. **The tooltip is vague.** index.html L447: "Allow safe tools to run without asking". Auto-run actually lets write, shell and exec tools run.

### Beat 3: What will change (tests first)

1. Add a new helper `chat/runtime-toggles.js` exporting `setupRuntimeModeToggles({ approvalToggle, verifyToggle, approvalBadge, verifyBadge, state, storage })`. It must:
   - restore `approvalToggle.checked` and `state.approvalAutoRun` from `readLastApprovalAutoRun()`
   - on `change`, write `state.approvalAutoRun`, `writeLastApprovalAutoRun()` and toggle `#approvalBadge`
   - on `change`, keep `state.verifyEnabled` in sync with the Verify toggle and toggle `#verifyBadge`
   - set both chips correctly on load

   `chat.js` gets one import and one call. L816 becomes `approvalAutoRun: !!approvalToggle?.checked`. `chat.js` stays at 1,045 lines or fewer.
2. If Jacob approves decision D2, run a one-time reset: if a migration marker is missing, write `'ask'` and set the marker.
3. Change the tooltip wording (decision D3).
4. Tests to write first, and confirm they fail on qa before the fix:
   - **Vitest `chat/runtime-toggles.test.js`** with fake DOM and storage:
     - saved `'run'` restores checked; saved `'ask'` or nothing restores unchecked
     - `change` saves the value and updates `state.approvalAutoRun`
     - the chips' `hidden` class follows both toggles
     - the one-time reset works (runs once, then respects the choice) if D2 is approved
   - **Vitest payload test:** `buildChatStreamPayload({approvalAutoRun:false})` gives `ask`, and `true` gives `run`.
   - **Vitest source contract:** `chat.js` never contains `!approvalToggle.checked`, calls `setupRuntimeModeToggles`, and stays at 1,045 lines or fewer.
   - **Smoke TC-14/15/16** (`/api/chat/stream` intercepted):
     - a fresh load sends `approval_mode: "ask"`
     - checking Auto-run sends `"run"` and shows the chip
     - after a reload, the choice and chip are still there
   - **Backend:** the existing gate tests (`tests/unit/safety/test_tool_policy_gate.py`, `test_tool_policy_kernel_gate.py`, `tests/unit/kernel/test_hitl_kernel_gate.py`) already cover `ask` parking and `run` allowing. Re-run them as-is; no backend change.
5. Proof for In Review:
   - Vitest shows the new tests passing, with only the known CARD-456 failures (5) left.
   - Smoke passes 16/16.
   - The gate unit tests pass.
   - Honesty gate passes, the broad `tests/unit` baseline holds, and CHANGELOG `[Unreleased]` has a **Security** line.
   - A Jarvis runbook screenshot showing the approval prompt with Auto-run off.

### Beat 4: What dies

- Silent auto-run on every default chat turn, and on the jobs and child agents it starts.
- The `!approvalToggle.checked` negation.
- The unused `readLastApprovalAutoRun`/`writeLastApprovalAutoRun` stop being unused (they get wired back in).
- Dead chips.
- The misleading "safe tools" tooltip.

---

## 2. Acceptance criteria (EARS)

- **[REQ-470-001]** WHILE `#approvalToggle` is unchecked, WHEN a chat turn is sent, THE SYSTEM SHALL send `approval_mode: "ask"`.
- **[REQ-470-002]** WHILE `#approvalToggle` is checked, WHEN a chat turn is sent, THE SYSTEM SHALL send `approval_mode: "run"`.
- **[REQ-470-003]** WHEN Chat loads with no saved choice, THE SYSTEM SHALL leave `#approvalToggle` unchecked (`ask`).
- **[REQ-470-004]** WHEN Chat loads, THE SYSTEM SHALL restore `#approvalToggle` from `autoreiv_approval_autorun`. WHEN the toggle changes, THE SYSTEM SHALL save `'run'` or `'ask'`.
- **[REQ-470-005]** WHEN `#approvalToggle` or `#verifyToggle` changes, and WHEN Chat loads, THE SYSTEM SHALL show `#approvalBadge` / `#verifyBadge` if and only if the matching toggle is checked.
- **[REQ-470-006]** WHEN either toggle changes, THE SYSTEM SHALL update `state.approvalAutoRun` / `state.verifyEnabled`, so Education follows the same choice.
- **[REQ-470-007]** (if D2 is approved) WHEN Chat first loads after this fix, THE SYSTEM SHALL reset a saved `'run'` to `'ask'` exactly once, and SHALL respect later choices.
- **[REQ-470-008]** THE SYSTEM SHALL NOT derive `approval_mode` from a negated `.checked` anywhere in `src/web/static`.
- **[REQ-470-009]** The Auto-run tooltip SHALL say that, when on, write and shell tools run without asking and blocked tools stay blocked.

## 3. Runbook on Jarvis (under 1 minute)

1. Reload Chat (Auto-run off, no chip). Ask for "create a wiki note titled test470". An approval prompt appears, and no note exists until you approve it.
2. Open options, check Auto-run. The Auto-run chip shows. Reload: it is still checked and the chip is still there.
3. Uncheck it again before normal use.

## 4. Decisions (all accepted by Jacob, 2026-09-24 11:52 PM ET)

- **D1: Default on a fresh install.** **Off (`ask`).** Fails safe. This matches `readLastApprovalAutoRun` and the backend default.
- **D2: Reset saved preferences once.** **Yes.** Reset a saved `'run'` to `'ask'` one time, using the marker key `autoreiv_approval_autorun_reset_470`. The UI has not shown the saved value since 2026-09-20, so nobody knowingly chose it.
- **D3: Wording.**
  - Tooltip: **"Off: AutoReiv asks before write, shell and code tools. On: they run without asking. Blocked tools stay blocked."**
  - Chip text when on: **"Auto-run ON"**, in amber rather than sky blue, as a warning.
- **D4: Education.** **Fold it in** through REQ-470-006. It uses the same state and adds no extra files. No separate card.
- **D5: Past sessions (accepted: no data fix).** Chats, jobs and handoffs started on 2026-09-20 or later with Auto-run unchecked ran gated tools without asking. There is no data fix. **If worried, review recent wiki, card and git changes.**

## 5. Constraints

- Frontend only. No backend change.
- `chat.js` stays at 1,045 lines or fewer (CARD-469 cap).
- Ship before the other chat cards, because this is a safety bug.
- **Until this ships:** leaving Auto-run **checked** actually means "ask". Unchecked means tools run without asking.

---

## 6. Build notes (2026-09-25 ET)

**Commits** on `feat/card-470-auto-run-toggle-fix` (from local qa `e91a2bfb`, not pushed):
- `577c7c2c` docs(cards): In Progress with decisions
- `b316e4c1` test(chat): red tests
- `8a544246` fix(chat): the fix
- `d8cb119a` docs(changelog): Security entry
- plus this In Review commit

**What changed**
- New `src/web/static/modules/studios/chat/runtime_toggles.js`:
  - `setupRuntimeModeToggles(state, {...})` restores the choice, saves changes, keeps `state.approvalAutoRun` / `state.verifyEnabled` in sync and drives both chips.
  - `resetSavedAutoRunOnce()` handles D2, using marker `autoreiv_approval_autorun_reset_470`.
  - Storage errors fail safe to `ask`.
- `chat.js`:
  - L816 is now `approvalAutoRun: !!approvalToggle?.checked`.
  - One import and one call were added. The scroll import was collapsed to one line.
  - 1,043 lines (cap 1,045).
- `index.html`:
  - The Auto-run tooltip uses the D3 text.
  - `#approvalBadge` is amber and reads "Auto-run ON", with its own tooltip.
- Backend unchanged. Education follows the toggle through `state.approvalAutoRun` (REQ-470-006).

**Red, then green**
- On qa code, the Vitest suite failed to load (module missing). With only the new module present, 3 source/template contracts still failed against qa's `chat.js` and `index.html`.
- On qa code, smoke TC-14..17 failed for the right reasons:
  - TC-14: got `run`, expected `ask`
  - TC-15: chip hidden
  - TC-16: nothing saved
  - TC-17: got `run` after a saved pre-fix `run`
- All of them are green after the fix.

**Proof**

| Suite | Result |
|---|---|
| `chat_runtime_toggles_470.test.js` | 11/11 |
| Vitest (full) | 825 passed, 5 failed (known CARD-456) |
| Smoke | 17/17 |
| Gate tests, unchanged (`test_tool_policy_gate.py`, `test_tool_policy_kernel_gate.py`, `kernel/test_hitl_kernel_gate.py`) | 15/15 |
| Broad `tests/unit` | 2015 passed, 11 skipped, 1 failed (known CARD-454) |
| Platform-pack suites | 124 passed, 5 skipped |
| ESLint | 4 errors / 5 warnings (unchanged baseline); new files clean |
| Honesty gate | green |

Tests ran only against scratch data. Live AppData was not touched.

**Scavenger Pass**
- `readLastApprovalAutoRun` / `writeLastApprovalAutoRun` are live again.
- The old tooltip text is gone from `src`.
- The negated `.checked` is gone. REQ-470-008 guards `chat.js`, `stream.js` and `education.js`.
- Noted, not changed: `coupleGoalAndVerify` in `chat/stream.js` is used only by tests (it was already unused before the split, so it is not a CARD-397 loss). It is out of scope.
- The Auto-run ON chip and the multi-phase `#goalBadge` are both amber. They are told apart by their text.

**Runbook on Jarvis**: section 3.

---

## 7. Live test round 1 failed, then fixed (2026-09-25 ET)

### What Jacob saw (~12:09 and ~12:10 AM ET, from his phone)
He hard-refreshed, left Auto-run unchecked and asked for a wiki note. He got no approval card, no reply, and no note.

### Diagnosis
Sources: the serve log, a read-only look at the live DB, and a repro on the scratch server with a fake tool-calling model.

The backend did the right thing:
- The phone created fresh sessions `ffcb7e81…` ("Create a note test470") and `18ef9a3f…` ("Create me a test note"), agent `autoreiv`.
- It sent `approval_mode: "ask"`.
- The model called `wiki_note_create`.
- The gate parked it: `pending_approvals` rows `appr_36d481b04e49` and `appr_7512d98f94b6` are still `pending`, and each tool message reads `Tool Error: approval_required:<id>`.
- No stream error was logged, so the CARD-469 "Reply failed" notice correctly did not show.
- Neither CARD-475 (screenshot poisoning) nor CARD-476 (no session) was involved.

The approval UI was lost in the CARD-397 split:
1. The tray poll asked for `?agent_id=<session id>` (log: `GET /api/approvals/pending?agent_id=18ef9a3f…`), so it matched nothing.
2. It read `data.pending`, but the API returns a bare array.
3. Its buttons (`.hitl-approve-btn`) never exist, and it rendered into the message list, which the finalize reload wipes.
4. The inline card had no listeners, and the finalize reload wiped it too.
5. Found while fixing: a first tap on the tray right after typing was swallowed, because the composer shrinks on blur (CARD-465) and moves the card before `pointerup`.

Pre-split `7b563003^` `chat.js` L1285-1370 and L3311-3360 had working versions of all of this.

### Fix
Commits `2d7049b9` (red tests), `c3e27a8f` (fix) and `be79085a` (CARD-343 contract moved). See the CHANGELOG. Scratch repro after the fix, with the fake model:
- The tray card appears with the tool name and arguments.
- Approve writes `scratch/smoke_data/wiki/00_Inbox/card_470_probe.md`.
- The turn resumes with `resume: true, approval_mode: "ask"`, the model replies "done", and the tray clears.

### Added requirements
- **[REQ-470-010]** WHEN a tool is parked for approval in the open session, THE SYSTEM SHALL show an Approve/Reject card in `#pendingHitlHost` that survives the finalize reload.
- **[REQ-470-011]** WHEN Approve or Reject is pressed, THE SYSTEM SHALL post the decision and, if the backend did not resume, resume the chat turn.
- **[REQ-470-012]** WHEN `approval_required` arrives live, THE SYSTEM SHALL render a working inline card, except for `goal_plan_review`.
- **[REQ-470-013]** A tap on an approval card SHALL NOT be lost to the composer's blur shrink.

### Proof (round 2)
| Suite | Result |
|---|---|
| Vitest | 839 passed, 5 failed (known CARD-456) |
| Smoke | 18/18 |
| Gate and HITL API tests, unchanged | 29/29 |
| Broad `tests/unit` | 2015 passed, 11 skipped, 1 failed (known CARD-454) |
| Honesty gate | green |
| ESLint | baseline unchanged |

### Follow-ups
- CARD-477: parked or failed tool rows say "✓ Complete". This predates the split.
- CARD-478: the Auto-run ON chip is the same colour as the goal chip.
- CARD-476 addendum: a stored active session is not restored.

### Live AppData
The two pending approvals from round 1 are still `pending` in live data. They will now show in the tray when Jacob opens those sessions. He can Reject them, or Approve if he wants the notes.

---

## 8. Merge note (2026-09-25 ET)

Jacob live-tested round 2 on Jarvis and replied `merge to qa`. `feat/card-470-auto-run-toggle-fix` was merged into qa with `--no-ff`. The full suites were rerun on qa before the push, and the only failures were the known CARD-454 and CARD-456 ones. Follow-ups CARD-476 (addendum), CARD-477 and CARD-478 are Ready.

