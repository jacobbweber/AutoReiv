---
id: CARD-511
title: "A Developer-built tool is registered without being run: check native and MCP tools once in the sandbox before they go live"
status: Ready
created: 2026-09-25
branch: qa
related:
  - ADR-0060
  - CARD-495
  - CARD-497
  - CARD-472
  - CARD-423
  - CARD-394
  - CARD-516
  - CARD-517
  - CARD-518
labels:
  - type:product
  - area:tools
  - P1
---

# [CARD-511] Check a Developer-built tool once in the sandbox before it is registered

> **Status**: In Progress (`build`, 2026-09-26 ~1:52 AM ET: Jacob accepted D1-D13 exactly as recommended, including folding CARD-517 in (D10). Branch `feat/card-511-tool-check` from qa `3e709376`. Refined earlier the same night at qa `6f066514`)
> **Created**: 2026-09-25 (CARD-495 audit F6)
> **Governing ADR**: [ADR-0060](../adr/0060-retire-the-agent-training-factory.md) (Accepted), decision **D6**: this card lands **before CARD-497** and keeps only the parts of `verification_battery.py` it needs, moved out of the Factory. CARD-497 then deletes the rest. This card is step 3 of 6: CARD-495 (Done), CARD-496 (Done), **CARD-511**, CARD-497, CARD-512, CARD-498.
> **Related**: CARD-497 (deletes `verification_battery.py`, `tool_synthesizer.py`, `factory_packets.py`), CARD-472 (Ask Developer), CARD-423 (native lane), CARD-394 (MCP engineering tools), CARD-516/517/518 (filed from this reproduction)
> **Labels**: `type:product`, `area:tools`, `P1` (raised from P2 because CARD-497 removes the only check there is)

## Gate language (exact reply phrases)

| Jacob reply | Meaning |
|-------------|---------|
| **`continue`** | Refine. No product code (this pass) |
| **`build`** | Build test-first on `feat/card-511-tool-check`, with the decisions as accepted |
| **`merge to qa`** | After In Review, and after the runbook passes on scratch and serve |

---

## 1. Four Beats

**Beat 1: What Jacob means.** When Developer builds a tool, either a native Python tool or an MCP server, AutoReiv runs it once in the sandbox before it goes live. A broken tool is never registered. Instead, the Developer chat, and the Tools Studio job if there is one, say plainly what failed, and Developer can fix the tool and try again. A good tool registers just as it does today. This replaces the Factory's Verify phase, so CARD-497 can delete the Factory without losing the only tool check.

**Beat 2: What AutoReiv does now.** Reproduced 2026-09-26 ~1:20 AM ET on a scratch server (port 8767, fresh data `scratch\c511_rb`, never Jacob's AppData). Scripts are `scratch\c511_repro.py`, `c511_repro2.py` and `c511_mcp_probe2.py`; the evidence is in `scratch\c511_repro_evidence.json`.

| Case | Call | Result today |
|---|---|---|
| Syntax error (`def run(**kw):\n    return (`) | `POST /api/tools/native`, low risk, no HITL, granted to autoreiv | **200, `success: true, persisted: true, mounted: true`** |
| Import error (`import nonexistent_c511_mod`) | same | **200, success/persisted/mounted** |
| Raises (`raise ValueError(...)` in `run`) | same | **200, success/persisted/mounted** |
| Good echo tool | same | 200, success/persisted/mounted |
| `GET /api/tools/native` | | Lists all 4 tools. Tools Studio shows them as "Native custom" |
| Invoke each (`/invoke`, agent autoreiv, `approval_mode: run`) | | The three broken tools fail **only now, at call time** (`SyntaxError`, `ModuleNotFoundError`, `ValueError` tracebacks from `autoreiv_sandbox_*`). The good tool returns `{"echo":"x"}` |
| Developer chat tool path | `NativeToolEngineeringTools.register_native_tool(...)`, the handler Developer calls in chat, on a fresh temp store, with import error plus syntax error, HITL, medium risk | **`success: true, persisted: true, mounted: true`** |
| MCP: server that cannot start (`python -c "import nonexistent_c511_mod"`) | `POST /api/settings/mcp` (same save path as Developer's `register_mcp_service`) | **200, `status: saved, mounted: true, tools_count: 0`** (CARD-516) |
| MCP: Settings **Test** on a server that cannot start (SDK missing) | `POST /api/settings/mcp/test` | **`status: ok`, 0 tools** (CARD-516) |
| MCP: server whose only tool crashes the process | `POST /api/settings/mcp` | **200, saved, mounted, 1 tool (`mcp_c511-mcp-raw_lookup`)**. Nothing called it |
| Calling that crashing MCP tool | `MCPClientAdapter.call_tool` | **`success: true, output: {}`**. The server raised and exited, and the adapter reported success (CARD-517) |
| Restart the scratch server (no wipe) | | All 4 native tools remount (`mount_persisted`, no check). All 3 MCP servers show `is_mounted: true` |

Where the gap is in the code (qa `6f066514`):
- **`native_packaging.py` `register()` (L119):** runs `_validate`, which checks the name regex, description, code ≤ 40k characters, the text `def run(`, the parameters dict and the risk level. It then saves the `native_custom_tools` setting, mounts, syncs the policy and grants the tool. **It never parses or runs the code.** Both `POST /api/tools/native` and Developer's `register_native_tool` chat tool call this one service (`app.py` L325-334).
- **`mcp_engineering_tools.py` `register_mcp_service` (L558):** saves `mcp_servers` first, then mounts. If mounting throws it still returns `success: true, saved: true`, and a failed `tools/list` does not even throw, because `MCPClientAdapter.list_tools` returns `[]` and puts the reason in `last_error`.
- **`test_mcp_server` (L277)**, which Developer uses as its MCP "test", only reads the AST. It never starts the server, yet reports "Simulated JSON-RPC handshake verified" and `jsonrpc_tested: true` (CARD-518).
- **`developer_mediation.py` L375 `verify_checker=None`:** this is the job-phase checker for the Author phase ("done when the developer has replied"). It cannot see the tool, and most Developer chats start from **Talk** (`open_chat`), which has no job at all. So wiring a checker at L375 alone would miss most tool registrations (see D1).
- **`verification_battery.py`** is Factory-shaped. It imports `EvalPacket` from `factory_packets` (deleted by CARD-497), runs Factory `test_code`, replays each tool 3 times, audits runbooks through `ToolSynthesizer`, and probes MCP servers with a Factory-only `{"action":"status"}` argument. Only `detect_path_safety_violation` (L69), the AST parse, and the idea "start the MCP server, list its tools, call one" are worth keeping.
- **"Sandbox" today** (`SandboxedSubprocessWorker`): a fresh temp directory, environment variables whose names contain KEY/TOKEN/SECRET/PASSWORD/AUTH/CREDENTIAL/PRIVATE removed, output capped, a timeout, and `CommandGuardrail` on the command line. **The network is not blocked and the file system is not jailed.** A tool that deletes a file, sends mail or posts to an API does that during the check too. The card must be honest about this (D5, D6).
- The AutoReiv venv has **no `mcp` SDK**, and Developer's `scaffold_mcp_server` writes `from mcp.server.fastmcp import FastMCP`. So a scaffolded server registered with the default stdio command cannot start here, and today it is saved as "mounted, 0 tools". The check will catch this and say so (noted in CARD-516).

**Beat 3: What changes.**
1. **New module `src/application/tools/tool_check.py`** (`ToolCheckService`, `ToolCheckResult`). It holds everything kept from `verification_battery.py`, and nothing in it imports `agent_training_factory` or `orchestration`.
   - `detect_path_safety_violation` moves here. `verification_battery.py` imports it back from here until CARD-497 deletes it.
   - **Native check:** stage 1 static (AST parse, `def run` exists at module level, path safety; `eval`/`exec` gives a warning only). Stage 2 import (run the module in the sandbox without calling `run`). Stage 3 one sample call through the **same** `_run_sandboxed` runner that invoke uses, with a 20 s timeout. The result must be JSON-serializable.
   - **MCP check:** start the server with the saved command and env through `MCPClientAdapter` (timeout 10 s, the same as Settings Test). `tools/list` must return at least one tool, with no `last_error`. Every tool needs a valid name and an object `inputSchema`. Then make one sample `tools/call` (20 s) that returns no JSON-RPC error, no `isError`, and does not end the server process. Close the adapter afterwards.
2. **`NativeCustomToolService.register`** runs the native check **before** it saves anything. On failure it saves, mounts, grants and syncs policy for nothing, and returns `success: false, registered: false, check: {...}`. On success the saved row carries a `check` block. Because both the operator API and Developer's chat tool use this service, they both get the check (single lever). `register` becomes `async`; the router and the chat handler await it.
3. **`MCPEngineeringTools.register_mcp_service`** runs the MCP check **before** it saves `mcp_servers`. On failure it saves nothing, mounts nothing, writes no companion skill, and returns `success: false` with the check. Settings Studio's hand attach (`POST /api/settings/mcp`) stays operator-owned and unchanged (D9).
4. **Sample input:** Developer passes a new optional `sample_arguments` to `register_native_tool` and `register_mcp_service` (plus `sample_tool` for MCP). Without it, the check builds a minimal input from the JSON Schema. The check itself never calls an LLM (D4).
5. **Skipping the call:** for high-risk tools, or when Developer passes `sample_call: "skip"` with a `skip_reason` (for example "needs an API key" or "sends email"), the static, import and list stages still run, and the tool registers with status **`checked_without_call`** and that reason shown (D5, D6).
6. **Failure reaches the operator:** the chat tool result, which Developer relays in chat, starts with `Not registered: <tool> failed the <stage> check` followed by the trimmed error. The Tools Studio job (when the chat came from **Submit**) records a `tools_studio_tool_check` journey event, and `GET /api/tools_studio/authoring/jobs/{id}` returns `tool_checks`. Retrying is just Developer fixing the tool and calling register again, since nothing was saved (D11).
7. **Durable state:** the native tool row gets a `check` block; the MCP server record gets the same; the job journey gets the event; the chat transcript holds the tool result. A failed attempt leaves only the journey event and the transcript, with no half-saved tool (D11).
8. The **`MCPClientAdapter` false success** on a crashed `tools/call` (CARD-517) is fixed here, minimally, because the MCP pass rule depends on it (D10).
9. `developer_mediation.py` L375 stays `verify_checker=None`, with a comment that points to `tool_check.py`. The phase rule is about the reply, and the tool check sits at registration (D1).

**Beat 4: Done when.**
- Through both `POST /api/tools/native` and Developer's `register_native_tool`, a syntax-error, import-error or raising tool is refused with a clear stage and error, and it does not appear in `GET /api/tools/native`, the Tools Studio catalog or any agent allowlist.
- A good tool registers as today and shows "Checked".
- Through `register_mcp_service`, a server that cannot start, lists no tools, or whose sample call crashes or errors is refused and not saved.
- `tool_check.py` imports nothing from the Factory, and CARD-497 can delete `verification_battery.py` entirely.

---

## 2. What must keep working (the regression fence)

- A good native tool registers with the same response fields as today (`success`, `persisted`, `mounted`, `granted_agent_ids`), plus `check`. Policy sync, HITL default, `requires_hitl` forced on for high risk, `_reject_foreign_collision`, `DELETE` and `invoke` are unchanged.
- **Tools already registered are not re-checked** and still mount at startup (`mount_persisted`). They show "Not checked" in Tools Studio (D12).
- Settings Studio MCP save, delete and Test are unchanged (CARD-516 covers their false "ok"). Agent MCP attach (`/api/agents/{id}/mcp`) is unchanged.
- Tools Studio **Talk** still opens a Developer chat with no job. **Submit** still creates one job with one Author phase and one Developer turn. `interpretAuthoringSubmit` still requires `persisted_tool: false` and `packaging_applied: false`, so the check result travels as a separate `tool_checks` field and never flips those (`tools_studio_authoring.js` L90-92).
- `plan_native_folder` does not register and does not run anything.
- Factory code keeps working until CARD-497 (it still imports `detect_path_safety_violation`, now re-exported).
- `test_mcp_server`, `scaffold_mcp_server` and `deploy_mcp_container` are unchanged (CARD-518 is separate).

---

## 3. Acceptance criteria (EARS)

- **REQ-511-001 (native, event):** WHEN a native tool is registered through `NativeCustomToolService.register` (operator API or Developer's `register_native_tool`), THE system SHALL run the static, import and sample-call stages before it saves, mounts, grants or syncs policy.
- **REQ-511-002 (native, unwanted):** IF any stage fails, THEN THE system SHALL NOT save the `native_custom_tools` row, mount the tool, change any agent allowlist or change tool policy, AND SHALL return `success: false`, `registered: false` and a `check` object naming the failed stage and a trimmed error (≤ 2,000 characters, last traceback line first).
- **REQ-511-003 (native pass):** A native tool SHALL pass only when the code parses, defines a module-level `run`, has no path-safety violation, imports in the sandbox, and one sample call returns a JSON-serializable result within 20 s.
- **REQ-511-004 (MCP, event):** WHEN Developer calls `register_mcp_service`, THE system SHALL start the server, list its tools and make one sample call **before** it writes `mcp_servers`, mounts, or writes a companion skill.
- **REQ-511-005 (MCP pass):** An MCP server SHALL pass only when it answers `tools/list` within 10 s with at least one tool and no adapter `last_error`, every tool has a valid name and an object `inputSchema`, and one sample `tools/call` returns within 20 s with no JSON-RPC error, no `isError`, and the server process still alive.
- **REQ-511-006 (MCP, unwanted):** IF the MCP check fails, THEN THE system SHALL NOT save or mount the server, AND SHALL return `success: false` with the check object.
- **REQ-511-007 (sample input):** WHERE `sample_arguments` is given, THE check SHALL use it (validated against the schema). Otherwise THE check SHALL build one from the schema: required properties only, using `default`, then the first `enum` value, then `""`, `0`, `false`, `[]` or `{}` by type. THE check SHALL NOT call an LLM.
- **REQ-511-008 (skip):** WHILE a tool is `risk_level: high`, or Developer passed `sample_call: "skip"` with a non-empty `skip_reason`, THE check SHALL skip only the sample call, register the tool if the other stages pass, and record status `checked_without_call` with the reason.
- **REQ-511-009 (sandbox unavailable):** IF the sandbox cannot start (spawn error, guardrail block, missing interpreter), THEN THE system SHALL NOT register the tool AND SHALL say "The check could not run: <reason>. Nothing was registered; try again." (fail closed).
- **REQ-511-010 (durable):** WHEN a check finishes, THE system SHALL store `{status, stages, sample_arguments, skip_reason, error, duration_ms, checked_at}` on the registered row (native row or MCP record) on pass or skip. WHEN the Developer session belongs to a Tools Studio mediation job, THE system SHALL also record a `tools_studio_tool_check` journey event, pass or fail, and `GET /api/tools_studio/authoring/jobs/{id}` SHALL return `tool_checks`.
- **REQ-511-011 (existing tools):** THE system SHALL NOT re-check or unmount tools registered before this card. Tools Studio SHALL show "Not checked" for rows without a `check` block, "Checked" for `passed`, and "Checked without a sample call: <reason>" for `checked_without_call`.
- **REQ-511-012 (no Factory):** `src/application/tools/tool_check.py` SHALL NOT import `agent_training_factory`, `orchestration.verification_battery`, `tool_synthesizer` or `domain.orchestration.factory_packets`. `verification_battery.py` SHALL import `detect_path_safety_violation` from `tool_check.py`.
- **REQ-511-013 (adapter truth):** IF an MCP stdio server returns no line for a request, or exits during it, THEN `MCPClientAdapter` SHALL raise (so `call_tool` returns `success: false`) instead of returning `{}` (CARD-517).
- **REQ-511-014 (Developer guidance):** THE Developer prompt and the `native-tool-engineering` / `mcp-engineering` skill text SHALL say that registration runs the tool once, how to pass `sample_arguments`, when to use `sample_call: "skip"`, and that on "Not registered" Developer fixes the tool and calls register again.

---

## 4. Decisions (decided 2026-09-26 ~1:52 AM ET: Jacob said `build` and accepted D1-D13 exactly as recommended, shown in bold)

| # | Question | Options | Recommendation |
|---|---|---|---|
| D1 | Where does the check run? | (a) `verify_checker` at `developer_mediation.py` L375; (b) inside `NativeCustomToolService.register` and `register_mcp_service` | **(b).** L375 checks the Author phase reply and has no tool to look at. Talk chats have no job at all, and the operator API bypasses mediation. (b) covers chat with or without a job, plus the API, in one place. L375 stays `None` with a comment |
| D2 | What is kept from `verification_battery.py` (ADR-0060 D6)? | Keep the whole battery / keep a slice / write from scratch | **Move only `detect_path_safety_violation` into `tool_check.py`**, re-exported so `verification_battery.py` keeps working. Re-implement "AST parse" and "start the MCP server, list, call one" on the existing `_run_sandboxed` and `MCPClientAdapter`. **Do not keep:** stage 3 replays ×3, stage 2 stderr signature heuristics, the ToolSynthesizer runbook audit, `is_shallow_stub_artifact`, the `{"action":"status"}` probe, `EvalPacket`, or `SandboxTestRunner` test_code. CARD-497 deletes the whole file |
| D3 | `eval`/`exec` and bare `except` (old stage 4) | Fail / warn / drop | **Warn only** (shown in `check.warnings`). Real tools use them; the old rule was aimed at generated Factory code. Path-safety violations stay a **failure** |
| D4 | Sample input: where does it come from? | (a) LLM-generated inside the check; (b) Developer-supplied `sample_arguments`, else built from the schema; (c) empty `{}` | **(b).** Developer is already the LLM and knows the tool, so it passes a realistic sample. The schema fallback keeps the check deterministic, with no model cost, no extra timeout and no flakiness. No LLM call inside the check |
| D5 | Side effects: do we always make the sample call? | Always / never for medium+ / skip only for high or on request | **Run it for low and medium. Skip automatically for high** (status `checked_without_call`, "high risk: sample call skipped"). Developer may also skip with a reason (D6). Most tools default to medium, so skipping medium would make the check mostly static. The runbook and the skill text tell Developer to pass a harmless sample (a dry-run or read-only argument) |
| D6 | Tools that need network or secrets | Fail / let Developer skip the call with a reason / inject secrets into the sandbox | **Developer may pass `sample_call: "skip"` with `skip_reason`.** Static, import and list still run, and the reason is shown and stored. The sandbox strips KEY/TOKEN/... variables and **no secrets are injected into the check**. The network is not blocked; a network call that fails is a failure unless skipped |
| D7 | Timeouts | | **Native: 20 s for the sample call** (the same as invoke), **10 s for the import stage. MCP: 10 s to start and list** (the same as Settings Test), **20 s for the call.** A timeout is a failure: "timed out after N s" |
| D8 | Sandbox unavailable | Fail closed / register with a warning | **Fail closed**, no override. Message: "The check could not run: <reason>. Nothing was registered; try again." A tool that was never run is exactly today's bug |
| D9 | Scope on the MCP side | Developer's `register_mcp_service` only / also Settings Studio save | **`register_mcp_service` only.** Settings save is the operator hand-attaching third-party servers (often needing secrets, with no safe sample call) and already has a Test button. Its false "ok" is CARD-516 (Ready, not recommended now) |
| D10 | Adapter reports success for a crashed `tools/call` (CARD-517) | Fix here / leave for CARD-517 | **Fix here, minimally** (one failing test first: an empty line or an exited process raises). The MCP pass rule cannot be trusted without it. CARD-517 closes with this card |
| D11 | Durable state and how failure is shown | | **Pass/skip: a `check` block on the native row and on the MCP record. Every attempt, pass or fail: a `tools_studio_tool_check` journey event when the session belongs to a mediation job** (find the job by `session_id`), plus `tool_checks` on `GET .../jobs/{id}` and in the submit response. The chat tool result carries the "Not registered: ..." text, so the transcript is the record for Talk chats. No new table. The phase checkpoint `verifier_status` goes from `none` to `passed`/`failed`/`skipped` only for a job whose turn registered something |
| D12 | Tools already registered | Re-check at startup / "Check now" button / leave alone | **Leave them alone**, and show "Not checked" in the Tools Studio catalog. Re-checking at startup would run side effects at boot and could unmount tools Jacob relies on. Re-registering a tool (same name) runs the check. A "Check now" button can be a later card if wanted (not filed) |
| D13 | Result model | Keep `EvalPacket` / new dataclass | **New `ToolCheckResult` dataclass in `tool_check.py`** (`status` passed/failed/checked_without_call/could_not_run, `stages[]`, `warnings[]`, `error`, `sample_arguments`, `skip_reason`, `duration_ms`, `checked_at`). `factory_packets.py` is deleted by CARD-497 |

---

## 5. Failing-tests-first plan

Write these first, confirm they fail on qa `6f066514`, then build.

**Unit, new file `tests/unit/tools/test_tool_check.py` (native):**
1. A good echo tool: status `passed`, three stages, sample built from the schema.
2. Syntax error: `failed` at `static`, the message contains `SyntaxError` and a line number, and the sandbox is not called (spy).
3. No module-level `run` (for example `run` only inside a class, or `def run(` inside a comment): `failed` at `static`.
4. Import error: `failed` at `import`, the message contains `ModuleNotFoundError: No module named 'nonexistent_c511_mod'`.
5. Raises on the sample: `failed` at `sample_call`, the message contains `ValueError: c511 deliberate failure`.
6. Non-JSON result (returns `object()`): `failed` at `sample_call`.
7. `time.sleep(30)`: `failed`, "timed out after 20 s" (patch the timeout to 1 s in the test).
8. Path traversal `open('../x')`: `failed` at `static`. `eval(...)` gives a warning only (D3).
9. High risk: `checked_without_call`, and the sample call is not run (spy). `sample_call="skip"` without a reason is rejected by `_validate`; with a reason it gives `checked_without_call`.
10. Schema sample builder: required, default, enum and type fallbacks. `sample_arguments` that violate the schema are rejected before running.
11. Sandbox spawn raises `OSError`: `could_not_run`.
12. `tool_check.py` has no forbidden imports (AST walk); `verification_battery.detect_path_safety_violation is tool_check.detect_path_safety_violation`.

**Unit, new file `tests/unit/tools/test_native_packaging_check.py` (there is no unit file for `native_packaging.py` today):**
13. Register a broken tool: `success false`, no `native_custom_tools` row, `tool_registry` has no tool, agent allowlist unchanged, policy setting unchanged.
14. Register a good tool: the row has a `check` block. The existing register tests still pass (awaited).
15. `mount_persisted` with an old row that has no `check`: it still mounts (D12).
16. `NativeToolEngineeringTools.register_native_tool` with a broken tool: the result text starts with `Not registered:`.

**Unit, MCP (`tests/unit/skills/test_mcp_engineering_tools.py` plus `tests/unit/mcp/test_mcp_client_adapter.py`):**
17. The adapter over a raw stdio fixture server whose tool exits the process: `call_tool` gives `success: false` (CARD-517; fails today with `success: true, output: {}`).
18. `register_mcp_service` with a server command that cannot start: `success false`, `mcp_servers` unchanged, no mount, no companion skill.
19. With a server that lists 0 tools: `failed` at `list`. With a tool whose sample call returns `isError`: `failed` at `sample_call`.
20. With a good raw fixture server: saved, mounted, with a `check` block on the record.
21. `sample_tool` naming a tool that does not exist: `failed` with the available names.

Fixtures: the raw JSON-RPC stdio servers under `tests/fixtures/mcp/` (copied from `scratch\c511_mcp\server_raw.py`, plus a good variant). They need no `mcp` SDK.

**Integration, mediation (extend `tests/integration/operator_contracts/test_oc422_tools_studio_developer_mediation.py`):**
22. After a turn whose tool call registered or refused a tool in the job's session, the job has a `tools_studio_tool_check` event, `get_job` returns `tool_checks`, and `persisted_tool` is still `false`.

**Integration, route (extend `tests/integration/operator_contracts/test_oc423_custom_tool_packaging.py`; oc425/oc426/oc427 must keep passing, so update any fixture code that would now fail the check):**
23. `POST /api/tools/native` with each broken tool: **422** with `check.stage` and `check.error`, and `GET /api/tools/native` does not list it. A good tool: 200 with `check.status == "passed"`.
24. `GET /api/tools/native` lists an old row without `check` with `check: null`.

**Vitest (extend `tests/unit/frontend/card_423_tool_packaging.test.js` and `card_422_tools_studio_authoring.test.js`):**
25. A native row with `check.status passed` shows "Checked", with `checked_without_call` shows the reason, with no check shows "Not checked".
26. `interpretAuthoringSubmit` passes `tool_checks` through and still throws on `persisted_tool: true`.

**Playwright smoke:** one new TC: seed one native tool through the API with a mocked check that fails (route mock) and one that passes; the catalog shows only the passing tool with "Checked", with 0 console errors, on desktop and phone.

**Full suites at In Review:** unit, integration, Vitest, smoke, ESLint and ruff. The only allowed failures are CARD-454/456.

---

## 6. Runbook (live test on Jarvis, after build)

Scratch first (`powershell -ExecutionPolicy Bypass -File scratch\c505_run.ps1 -Data c511_live -Wipe -Tag c511l`, port 8767), then serve on 0.0.0.0:8000.

1. **Replay the reproduction:** `.venv\Scripts\python.exe scratch\c511_repro.py`. Expect `c511_syntax_err`, `c511_import_err` and `c511_raises` to get **422 "Not registered"** with the stage and error, and `c511_good` to get 200 with `check.status: passed`. `GET /api/tools/native` lists only `c511_good`.
2. **Developer, native, good:** Tools Studio, **Talk**: "Make a tool `c511_word_count` that counts words in `text`." Developer registers it. The chat shows it registered after one check run. Tools Studio catalog shows **Native custom · Checked**. Calling it from AutoReiv chat works.
3. **Developer, native, broken:** in the same chat: "Register `c511_broken_import` that does `import nonexistent_c511_mod` in a `run` that returns 1. Don't fix it." The chat shows **"Not registered: c511_broken_import failed the import check, ModuleNotFoundError ..."**. It is not in the catalog.
4. **Retry path:** "Now fix it and register it again." It registers and shows "Checked".
5. **Skip path:** "Make a high-risk tool `c511_send_note` that would send a message (just return the text)." It registers as **"Checked without a sample call: high risk"**, and HITL still parks it when called.
6. **Submit job:** Tools Studio **Submit** with a create intent for `c511_bad_submit` and "make it raise on purpose". The job detail (`GET /api/tools_studio/authoring/jobs/{id}`) shows `tool_checks` with `failed`, and the chat shows the error. Nothing new appears in the catalog.
7. **MCP:** in Developer chat: "Register an MCP server named c511-raw with command `<venv python> -u D:\Projects\Active\AutoReiv\scratch\c511_mcp\server_raw.py`." It is **refused** (the sample call crashed the server), and Settings MCP does not list it. Then try `python -c "import nonexistent"`: refused, "server did not answer tools/list: ...".
8. **Existing tools:** on serve (Jacob's data), tools registered before the build still work and show **"Not checked"**. Nothing was unmounted.
9. Restart serve (`scripts\restart_serve.ps1 -HostAddr 0.0.0.0 -Port 8000`); health returns 200 on 127.0.0.1 and 192.168.1.99. Repeat steps 2-3 on the phone.

---

## 7. Definition of done

- REQ-511-001..014 pass.
- Tests are written first and were seen failing.
- Full suites pass, apart from the known CARD-454/456 failures.
- The runbook passes on scratch and serve (desktop and phone).
- `tool_check.py` is Factory-free, and CARD-497's card is updated to delete `verification_battery.py` whole.
- CARD-517 is closed with this card.
- The card is set to In Review with evidence, then Done at `merge to qa`.

## What stays out of scope

- Settings Studio MCP save/Test false "ok" (CARD-516). `test_mcp_server`'s simulated handshake (CARD-518).
- Network or file-system jailing of the sandbox.
- Re-checking tools already registered, and a "Check now" button.
- Scenario replay (ADR-0060 D3).
