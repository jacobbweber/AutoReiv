# [CARD-172] Agent Training Factory: Intent Distill, scenario battery, Reflexion outer rinse

> **Status**: Ready
> **Created**: 2026-09-06
> **Spec Reference**: CARD-171; docs/specs/agent-pack-factory/; Reflexion / Self-Ask / CoVe (industry patterns, no third-party product names in code)
> **Labels**: `type:architecture`, `type:feat`, `AutoReiv.Orchestration`, `AutoReiv.Wiki`

---

## 1. Why / Intent

CARD-171 replaced costume FactoryRunner with a phase registry (Ground → Blueprint → Author → Verify → Optimize → Promote). Live Hyper-V use showed the gap: the agent can clarify with the human, but training still **stamps** tools that mention a domain without forcing the Factory to learn **how a professional does it** (e.g. Gen2 Autounattend must be on bootable media / ISO, not a folder DVD).

**Walked (2026-09-06 Jacob):** Extend Agent Training Factory with domain-agnostic **research / question batteries**, **scenario verification**, and **Reflexion-style loops**. Do **not** hard-wire Hyper-V (or any product) into the orchestrator. Use proven patterns: Self-Ask / least-to-most, grounded Wiki SOP, Chain-of-Verification style scenario checks, Reflexion (fail → lesson → retry), critique–revise. Inner vs outer rinse locked below.

Keep Train / Lab Monitor / backlog / auto-train / promote surfaces. Build on `agent_training_factory` phase registry (thin list + rinse edges; no nested meta-engine).

Do not implement until Jacob says **build**.

---

## 2. Locked decisions

### Phase pipeline (extends CARD-171)
1. **Intent Distill** (new) — question battery → structured intent answers  
2. **Ground** — Wiki SOP + medium map from those answers (+ official/how-a-pro-does-this research into Wiki)  
3. **Blueprint** — skills/tools **and** scenario done-whens (capability matrix)  
4. **Author** — write against Wiki + scenarios  
5. **Scenario Verify** (new battery) — does runbook/tool cover each scenario claim?  
6. **Code Verify** — existing AST/safety/idempotency battery  
7. **Optimize** → **Promote** (HITL)

### Learning loops (locked)
| Loop | When | Edge | Cap |
|------|------|------|-----|
| **Inner rinse** | Scenario or Code Verify fail (implementation gap) | → Author with fail reason + last critic notes | `max_verify_rinses` (default 3) |
| **Outer rinse** | Repeated fails that are **how/SOP / misunderstanding** (not just bad code) | → Intent Distill + Ground with failure lessons → refresh Wiki → Blueprint only if skill/tool shape changed → Author → Verify | `max_outer_rinses` (default 2) |

Re-ask **only questions implicated by the failure** on outer rinse, not the entire battery every time. Both loops terminal-fail the job with visible reasons in Lab Monitor (same as CARD-171 rinse UX).

### Intent Distill — default question battery (domain-agnostic)
Exact wording can be tuned at implement; intent of each question is locked:
1. What is the operator trying to achieve (outcome)?  
2. What constraints did they give (paths, env, gen, credentials policy)?  
3. What target medium (cli/api/host/files)?  
4. What would a professional SOP include for this role/task?  
5. What official or standard guidance should be consulted?  
6. What is still unknown / must be clarified or assumed?  
7. What scenarios prove the capability works (done-whens)?

Answers + later Reflexion lessons land in Wiki with Factory front-matter contract (CARD-171 v1).

### Anti-goals
- No Hyper-V / finance / product-specific `if` in the orchestrator.  
- No nested phases-of-phases meta-engine.  
- No silent fallback to shallow synthesizer success when scenarios fail.  
- Do not copy pack skills into `$DATA_DIR/skills` (CARD-171 cleanup stays).

---

## 3. What to Build

1. Add **Intent Distill** and **Scenario Verify** phase modules to `src/application/agent_training_factory/`; update registry order + rinse edges (inner + outer).  
2. Persist `max_outer_rinses`, outer rinse count, and “failure class” (implementation vs sop/how) on the factory job.  
3. Scenario Verify reads Blueprint capability matrix; fails with concrete missing scenarios; feeds Author (inner) or Intent Distill (outer).  
4. Ground++ writes/updates Wiki SOP from distill answers; outer rinse appends Reflexion lessons to Wiki.  
5. Lab Monitor: show Intent Distill / Scenario Verify stages; feed lines for inner vs outer rinse and reasons.  
6. Tests (TDD): question battery structure; outer rinse triggers after SOP-class fails; inner does not re-Ground; caps terminate; no product hardcoding.  
7. Update agent-pack-factory spec/ADR pointers; CHANGELOG Unreleased. Status **In Review** after code. Not Done until Jacob live-tests. Local `qa` only.

---

## 4. Acceptance Criteria

- [ ] Intent Distill runs before Ground with structured answers in Wiki/packets.  
- [ ] Blueprint includes scenario done-whens; Scenario Verify can fail independently of Code Verify.  
- [ ] Inner rinse → Author only; outer rinse → Intent Distill + Ground with lessons; both capped; reasons visible.  
- [ ] No domain-specific orchestrator branches.  
- [ ] Unit/vitest green; ruff clean. In Review; not Done until live test.

---

## 5. Constraints

- Work on `qa`. Do not push unless Jacob asks.  
- Follow AGENTS.md walk + `.agents` TDD/FE/architecture rules.  
- CARD-171 remains In Review until Jacob signs Hyper-V pack + this follow-through as he chooses.  
- Do not start finance training as part of this card.

---

## 6. Pickup

Say **build** / **continue**. Prefer a Hyper-V template/unattend live retrain after implement to prove Gen2 boot-media scenario without hardcoding Hyper-V in Factory code (scenario text comes from distill/brief).
