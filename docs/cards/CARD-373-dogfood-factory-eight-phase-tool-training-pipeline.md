# [CARD-373] Dogfood Factory Eight Phase Tool Training Pipeline

> **Status**: In Review  
> **Created**: 2026-09-19  
> **Spec Reference**: none  
> **Labels**: `type:dogfooding`, `factory`, `tools`, `code-generation`, `verification`

---

## 1. Why / Intent
Dogfood and live-validate the Agent Training Factory 8-phase tool creation pipeline (`intent_distill` $\rightarrow$ `ground` $\rightarrow$ `blueprint` $\rightarrow$ `author` $\rightarrow$ `scenario_verify` $\rightarrow$ `verify` $\rightarrow$ `optimize` $\rightarrow$ `promote`), verifying that the generated Python tools and `SKILL.md` runbooks compile, pass syntax and type validation, adhere to the Matt Pocock progressive disclosure pattern, respect the $\le 7$ tools ceiling, and export cleanly into user-data packs without corrupting existing agents.

---

## 2. Three Beats

### Beat 1: What Jacob Means
When an operator seeds an objective in Factory Studio, the multi-phase pipeline must produce robust, working Python code and a clear `SKILL.md` runbook rather than hallucinated imports, syntax errors, or unmaintainable bloat. Jacob wants verification that a full training run from seed intent to final promotion yields a functional custom agent pack ready to use in Chat Studio.

### Beat 2: What AutoReiv Does Now
- The Factory pipeline is defined with 8 nodes (`intent_distill`, `ground`, `blueprint`, `author`, `scenario_verify`, `verify`, `optimize`, `promote`) in `src/application/agent_training_factory/`.
- While individual phase transitions are covered by isolated unit tests, there is no end-to-end integration dogfooding run that executes the complete pipeline, checks the generated Python AST, validates Pydantic model schemas, tests runtime import safety, and asserts that the promoted agent pack is recognized by the live agent registry in user data.

### Beat 3: What Will Change
- Create an automated end-to-end dogfooding test suite (`tests/integration/factory/test_dogfood_factory_pipeline.py`) simulating a realistic training job through all 8 phases.
- Assert that `author` outputs clean Python tool code with typed parameters and structured envelopes.
- Assert that `verify` and `scenario_verify` validate syntax via Python AST and catch invalid syntax before promotion.
- Assert that `promote` checks tool collisions, generates the agent profile with `origin="custom"`, and writes pack files into `$DATA_DIR/packs/<slug>/`.
- Assert that the newly promoted pack is immediately discoverable in `AgentRegistry` and loadable by `AgentKernel`.

---

## 3. Acceptance Criteria (Definition of Done)
- [x] Complete 8-phase factory pipeline advances sequentially from `intent_distill` through `promote`.
- [x] Generated Python tool code parses cleanly with `ast.parse()` with zero syntax errors.
- [x] Generated `SKILL.md` complies with Matt Pocock progressive disclosure standards and valid frontmatter.
- [x] Tool entropy budget ($\le 7$ tools) is verified on the deliverable.
- [x] `promote` writes pack files strictly to user data `packs/<slug>/` with zero checkout pollution.
- [x] Promoted agent is tagged with `origin="custom"` and registers into `AgentRegistry`.
- [x] Automated regression tests pass via `pytest tests/integration/factory/test_dogfood_factory_pipeline.py`.
- [x] Zero lint errors via `ruff check src tests`.
- [x] All 7 preflight gates pass cleanly.

---

## 4. Constraints & Honor Flags
- Standard honor constraints apply.
- Zero writes to repo root or checkout live data.
- Single isolated `feat/card-373-dogfood-factory-pipeline` branch cut from `qa` upon Jacob's `build` approval.
