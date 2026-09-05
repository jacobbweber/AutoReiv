# [CARD-166] Target Environment Grounding, Cmdlet Namespace Qualification, and Lab Pre-Flight Smoke Probing

> **Status**: In Review
> **Created**: 2026-09-05
> **Spec Reference**: docs/specs/agent-pack-factory/
> **Labels**: `type:feature`, `AutoReiv.Orchestration`, `AutoReiv.Packs`, `AutoReiv.Kernel`

---

## 1. Why / Intent

When executing host commands inside operational tools synthesized by the factory or bundled in agent packs, generic command names (e.g. `Get-VM`, `New-VM`, `Start-VM`) can collide with identically named cmdlets or binaries from other installed system administration modules on the operator's machine.

Furthermore, the Lab's verification sandbox previously relied exclusively on mock/dry-run checks (`dry_run=True`), allowing tools that collided with the host environment to pass through all 4 sandbox stages without detecting that an unrelated subsystem intercepted the command.

This card delivers end-to-end environment grounding:
1. **Cmdlet Namespace Qualification**: Fully qualifies target cmdlets and explicitly imports the target module to isolate commands from ambient namespace collisions.
2. **Domain-Agnostic Environment Discovery**: Grounds the Lab's discovery probe in the agent's purpose (intent and objectives) to detect the execution medium (OS CLI, Network API, Database, Pure Code) and inspect available modules dynamically.
3. **Live Sandbox Pre-Flight Smoke Probe**: Extends the Lab verification battery to execute a non-destructive live environment probe (verifying command resolution and clean status query) so collisions are caught before deployment.

---

## 2. What to Build

### Slice 1: Cmdlet Namespace Qualification & Module Isolation
- In `src/application/orchestration/tool_synthesizer.py`:
  - Fully qualify all virtualization cmdlets: `Hyper-V\Get-VM`, `Hyper-V\New-VM`, `Hyper-V\Start-VM`, `Hyper-V\Stop-VM`, `Hyper-V\Restart-VM`, `Hyper-V\Checkpoint-VM`, `Hyper-V\Get-VMSnapshot`, `Hyper-V\Remove-VM`, `Hyper-V\Get-VMSwitch`, `Hyper-V\New-VHD`, `Hyper-V\Add-VMHardDiskDrive`.
  - Prepend `Import-Module Hyper-V; ` inside `_run_powershell` in both the synthesized Python wrapper and PowerShell script.
- In live agent pack (`packs/hyperv/tools/manage_hyperv.py`, `packs/hyperv/tools/manage_hyperv.ps1`):
  - Update all cmdlet invocations with `Hyper-V\` qualification and explicit module import.

### Slice 2: Domain-Agnostic Discovery & Live Sandbox Smoke Probe
- In `src/application/orchestration/factory_runner.py`:
  - Update `_step_discovery_probe` to dynamically analyze the agent's purpose (`seed_intent`, `objectives`), detect the target medium, and probe the host for target module existence and namespace boundaries rather than returning static mocks.
- In `src/application/orchestration/tool_synthesizer.py` & `src/application/orchestration/verification_battery.py`:
  - Enhance verification test generation to perform an active environment smoke check (`action="status"`, ensuring success is not intercepted by foreign subsystem errors).
  - Surface environment probe diagnostics in `EvalPacket` so operators can see exact environment readiness in the Lab monitor.

---

## 3. Acceptance Criteria (Definition of Done)

- [x] [REQ-FACT-029] `ToolSynthesizer` generates PowerShell scripts and Python wrappers with fully qualified module prefixes (`Hyper-V\<cmdlet>`).
- [x] [REQ-FACT-030] `ToolSynthesizer` ensures `Import-Module Hyper-V; ` is executed before cmdlet evaluation.
- [x] [REQ-FACT-031] `manage_hyperv(action="status")` executes cleanly against the local Hyper-V host without colliding with other installed modules.
- [x] [REQ-FACT-032] `factory_runner.py` discovery probe dynamically resolves target environment boundaries and checks for module availability.
- [x] [REQ-FACT-033] Sandbox battery executes an environment smoke check that fails if a live command encounters subsystem collision or missing target errors.
- [x] Automated unit tests in `tests/unit/orchestration/test_tool_synthesizer.py` and `tests/unit/orchestration/test_verification_battery.py` pass cleanly.
- [x] Zero lint errors via `ruff check .`.

---

## 4. Constraints & Honor Flags

- Zero third-party product names in card, UI, notes, or CHANGELOG.
- Preserve all existing parameter signatures and return types on `manage_hyperv`.
- Domain-agnostic discovery must gracefully handle non-CLI agents (e.g. API, database, or pure computation agents).
