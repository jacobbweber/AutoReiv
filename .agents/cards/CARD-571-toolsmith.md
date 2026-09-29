---
id: CARD-571
title: "Toolsmith: restore runtime tool building and Ask Developer on the CARD-570 setup"
status: Ready
created: 2026-09-29
branch: feat/card-571-toolsmith
related:
  - CARD-570
  - CARD-562
  - CARD-539
  - CARD-520
  - CARD-511
labels:
  - type:feature
  - area:tools
  - P2
needs_decision: none
milestone: M25
proof: "unit tests for the builder agent's tool list (no shell, no code runner, no enable route), the Ask Developer entry points reaching the builder, and register -> check -> saved-not-mounted -> Jacob enables -> attach proposal accepted -> tool used by the target agent; guard test that no agent tool can enable a tool or skip the check; ruff clean; fast preflight --base qa GREEN; full not-slow suite 0 failed; live: from a chat 'no agent covers this' reply, Ask Developer -> the builder saves a tool -> Tools Studio shows it Not enabled -> Jacob enables it and accepts the attach proposal -> the target agent calls it; changing its code shows 'Approve new code' and stops it"
---

# [CARD-571] Toolsmith: restore runtime tool building and Ask Developer

> **Status**: Ready
> **Related**: CARD-570 (tools are files with approval hash and Jacob-only enable), CARD-562 (parked tool building off Developer), CARD-539 (attach_tool_to_skill proposals, Ask Developer from chat), CARD-520 (Observability Ask Developer), CARD-511 (tool check before save)
> **Labels**: `type:feature`, `area:tools`, `P2`

## Why

CARD-562 parked tool building: Developer lost `native-tool-engineering`, `mcp-engineering`, `capability-authoring`, `execute_code` and `cli_exec`, and every Ask Developer path now answers "Building tools with Developer is paused until M25 slice 2" (`developer_mediation.py` `TOOL_BUILDING_PARKED_MESSAGE`). CARD-570 then gave runtime-built tools a safe home: files in data `tools/<name>/` (`tool.py` + `tool.json`), `tools/.approvals.json` with the approved code hash, an enable only Jacob can flip (Tools Studio > Runtime-built tools), and agent tool grants only as `attach_tool_to_skill` proposals. The safety rails exist; nothing can use them. This card turns tool building back on, on top of those rails, without giving any agent a shell or code runner.

## What exists today (qa, after CARD-570)

- **Build path**: `register_native_tool` (skill `native-tool-engineering`, shipped but on no agent) -> tool check (static: parses, has `def run`, path safety, warns on eval/exec; then import and one sample call in `SandboxedSubprocessWorker`: temp folder, 20 s timeout, output cap, secrets stripped from env) -> saved to data `tools/<name>/`, not mounted until Jacob enables it; `target_agent_id` files an attach proposal.
- **Enable**: `POST /api/tools/native/{name}/enable|disable`, only from the Tools Studio panel; guard test keeps agent tools away from it. Changed code -> `needs_reapproval`, not mounted.
- **Grants**: an agent adding a tool to a skill becomes a pending `attach_tool_to_skill` proposal; Jacob's own Studio saves apply directly. Accepting a proposal does not check that the tool is enabled.
- **Ask Developer entry points** (all open a Developer chat with a draft): chat "no agent covers this" reply (CARD-539), Teach modal, gap backlog, Tools Studio Talk/Jobs (`/api/tools/authoring/*`), Observability tool escalation (CARD-520). All end at the parked message.
- **Other shipped skills, on no agent**: `capability-authoring` (propose/commit skills and tools), `mcp-engineering` (scaffold, test, deploy Docker MCP servers), `proposals` (on AutoReiv).

## Constraint (CARD-562 lesson)

Process is enforced in tools, not skill text. The builder never gets `execute_code`, `cli_exec` or any general shell or code runner. Its only way to run code is the tool check inside `register_native_tool`. It cannot enable, approve or grant; it can only save a disabled tool and file proposals.

## Scope

1. The builder agent (D1) gets a small skill set: `native-tool-engineering` (register, plan) and a read-only look at existing tools and skills. No shell, code runner, enable, or `commit_skill`.
2. Remove the parked message and the `park_developer_tool_building` leftovers; every Ask Developer entry point opens a chat with the builder (D2), with the draft carrying `target_agent_id`.
3. The builder's register call saves the tool disabled and files one attach proposal for the target agent (D5).
4. Tools Studio: one place listing saved tools with check result, code, Enable / Approve new code, and the linked attach proposal.
5. The tool check stays the gate before save (D3); what a built tool may touch follows D4.
6. Platform skill text (native-tool-engineering, capability-authoring) updated to match; system prompt of the builder says it builds tools only.
7. Tests and guard as in `proof:`; update `docs/` and the CHANGELOG.

Out of scope: MCP server building and Docker deploys (`mcp-engineering`), agents writing new agents, and any change to how Developer works cards.

## Decisions for Jacob

- **D1 - Who builds tools?** (a) a new shipped Toolsmith agent with only tool-building skills; (b) Developer again, with tool-building skills added back; (c) AutoReiv. Recommendation: (a). Developer stays a card worker with its hard rules; Toolsmith's tool list is small enough to check by eye.
- **D2 - Who can start Ask Developer?** (a) only Jacob, via the existing buttons (chat reply, Teach, gap backlog, Tools Studio, Observability); (b) also any agent via a hand-off tool; (c) only AutoReiv as a router. Recommendation: (a). Every build starts from a click by Jacob; nothing new to secure.
- **D3 - What must a built tool pass before Jacob can enable it?** (a) today's tool check (parses, has run, path safety, imports and runs once in the sandbox) plus Jacob reading the code in Tools Studio; (b) (a) plus a test case the builder must supply that passes; (c) (a) plus a second agent's review. Recommendation: (a). It already exists and Jacob reviews the code when enabling; add (b) later if tools break in use.
- **D4 - May built tools use the network or files?** (a) no network, files only in the sandbox temp folder, blocked by the check (reject imports like socket, requests, subprocess, and absolute paths); (b) allowed, but shown as a warning in Tools Studio before enabling; (c) allowed freely. Recommendation: (b). The current sandbox is a temp folder and a timeout, not a real network or file wall on Windows, so (a) would promise more than it enforces; a clear warning plus Jacob's enable is honest and simple. Choose (a) if you want built tools to be pure helpers only.
- **D5 - How is attaching the tool to an agent's skill approved?** (a) one step: enabling the tool in Tools Studio also accepts its pending attach proposal (shown together); (b) two separate approvals, enable then accept; (c) the builder's proposal only, enable not required. Recommendation: (a). One click, one decision, and a proposal for a tool that is not enabled no longer grants a dead name. Fix today's gap either way: accepting an attach refuses a tool that is not enabled.
- **D6 - Can the builder change an existing tool?** (a) yes, saving new code puts it back to "Approve new code" (already how CARD-570 works); (b) only tools it built; (c) no, new tools only. Recommendation: (a). The hash already stops changed code until Jacob re-approves, so nothing extra is needed.

## Decisions (Jacob, 2026-09-29: all six recommendations)

- **D1 = (a)**: a new shipped Toolsmith agent (`platform/agents/toolsmith.md`). Tools: register and plan tools, plus a read-only view of tools and skills. No shell, code runner, enable or `commit_skill`.
- **D2 = (a)**: only Jacob starts it, through the existing Ask Developer buttons. The paused message and the park step go; every button reaches Toolsmith with the target agent.
- **D3 = (a)**: today's tool check, plus Jacob reads the code when he enables it.
- **D4 = (b)**: network and file access are allowed; the check detects them and Tools Studio shows a clear warning before enabling. No claim of sandbox isolation.
- **D5 = (a)**: enabling the tool also accepts its pending attach proposal in one step. Gap 1 fixed: accepting an attach proposal refuses a runtime tool that is not enabled.
- **D6 = (a)**: Toolsmith may change existing tools; new code returns to "Approve new code" through the hash.
- Plus a guard test: no agent tool can enable a tool or skip the check.

## Done when

- Decisions recorded; the builder agent exists with the agreed tool list and no shell or code runner (guard test).
- Every Ask Developer entry point reaches the builder; the parked message is gone.
- The end-to-end flow in `proof:` passes live; changing a tool's code stops it until re-approved.
- Checks: ruff clean, fast preflight `--base qa` GREEN, full not-slow suite 0 failed.

## Research notes (2026-09-29)

- Before CARD-562 (`eece8249`), Developer had `native-tool-engineering`, `mcp-engineering`, `capability-authoring` (with `scaffold_agent_pack`, `export/import_agent_pack`), `proposals`, `build-agent-pack`, and `execute_code` / `cli_exec` in its tool list. Its prompt told it to use them for Ask Developer. The pack tools were removed in CARD-569.
- Hermes: agents write skills (text) with `skill_manage`; code runs through a dangerous-command approval gate. OpenHuman: each tool is classed allow / needs-approval / deny / hidden per session. Neither lets an agent put new code into use without a human gate, which matches the CARD-570 rails.

## Log

- 2026-09-29: Drafted from read-only research; decisions D1-D6 pending.
- 2026-09-29: Jacob chose all six recommendations; Ready.
