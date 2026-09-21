---
id: CARD-412
title: "Test Suite Hygiene, Obsolete Test Pruning, and Consolidation Audit"
status: Ready
created: 2026-09-21
adr: none
labels:
  - type:refactor
  - area:tests
  - area:hygiene
---

# [CARD-412] Test Suite Hygiene, Obsolete Test Pruning, and Consolidation Audit

> **Status**: Ready  
> **Created**: 2026-09-21  
> **ADR Reference**: none  
> **Labels**: `type:refactor`, `area:tests`, `area:hygiene`  

---

## 1. Why / Intent (Beat 1: What Jacob Means)

AutoReiv currently runs **1,854 unit tests** taking over **4.5 minutes** per run on developer machines.

Through hundreds of architectural iterations and card cycles (CARD-001 through CARD-409), substantial portions of the test suite have accumulated severe **test bloat and brittleness**:
- Tests that assert obsolete internal implementation details rather than observable system behavior.
- Legacy tests that test retired or superseded subsystems (e.g. older Assistant packs, archived RTM artifacts, retired weekly tools, legacy prompt shapes).
- Over-mocked whitebox tests that break upon harmless refactors, forcing engineers to spend hours updating historical string assertions rather than building features.

**Jacob's Question**: Is it worth stripping them down substantially, consolidating, or starting fresh on bloated areas?

**Goal**:
Execute a comprehensive **Test Suite Scavenger Pass**:
1. Identify and excise dead/zombie tests that test retired systems.
2. Replace dozens of brittle whitebox tests with lean, high-leverage contract & integration suites.
3. Radically speed up test execution (targeting `<60 seconds` for the entire backend suite).
4. Preserve critical negative regression assertions while eliminating test drag.

---

## 2. What AutoReiv Does Now (Beat 2: Current Test Landscape & Pain Points)

1. **Test Proliferation**:
   - Over 1,850 tests across dozens of subdirectories (`tests/unit/agent_packs`, `tests/unit/agents`, `tests/unit/skills`, `tests/unit/wiki`, etc.).
2. **Brittle Whitebox Assertions**:
   - Tests assert exact hardcoded lists of tools or skill strings (e.g. `assert "wiki" in agent.allowed_skill` or expecting exact 9 tool groups) rather than testing capability contracts.
3. **Execution Latency**:
   - Running `pytest -q tests/unit/` takes **275 seconds** (~4.5 minutes), slowing down pair-programming loops and creating high cognitive drag during verification passes.
4. **Orphaned Test Fixtures**:
   - Mocks and fixtures for deprecated classes continue to run in every CI/preflight cycle.

---

## 3. What Will Change (Beat 3: Technical Approach & Hypotheses)

### Strategy: Subtractive Test Engineering

1. **Test Inventory & Triage Pass**:
   - Categorize all 1,854 tests into 3 buckets:
     - **Bucket A (Essential Invariants & Negative Assertions)**: Security gates, boundary hygiene, single-lever invariants, schema validators, honesty smoke gates. *KEEP & LOCK.*
     - **Bucket B (Redundant / Overlapping Permutations)**: 20 tests testing minor variations of the same regex or helper. *CONSOLIDATE into parameterized tests.*
     - **Bucket C (Dead / Zombie Tests)**: Tests asserting behavior of retired features, deleted tools, or archived architectures. *PRUNE IMMEDIATELY.*
2. **Blackbox Contract Transition**:
   - Shift from whitebox internal state checks (`assert agent._internal_variable == 'xyz'`) to API & behavior contracts (`assert response.status_code == 200` and `assert payload.capabilities has ...`).
3. **Pytest Performance Optimization**:
   - Eliminate redundant SQLite disk I/O in tests that can use `:memory:`.
   - Parallelize test execution with `pytest-xdist` (`-n auto`).

---

## 4. What Dies Today (Beat 4: The Prune List)

- **PRUNE**: All test cases asserting legacy, retired platform tools and skills.
- **PRUNE**: Brittle duplicate test files covering superseded historical cards.
- **PRUNE**: Redundant multi-minute test execution delays.

---

## 5. Acceptance Criteria (EARS Syntax)

- **[REQ-412-001] Test Suite Dead-Code Elimination**:
  - *Ubiquitous*: THE SYSTEM SHALL contain zero test cases asserting against retired symbols, superseded tools, or archived pack structures.
- **[REQ-412-002] Execution Speedup**:
  - *Ubiquitous*: THE SYSTEM SHALL complete the full backend unit test suite in under 60 seconds on standard development environments.
- **[REQ-412-003] Zero Regression Coverage Loss**:
  - *Ubiquitous*: THE SYSTEM SHALL retain 100% of critical security, boundary hygiene, and negative regression assertions.

---

## 6. Constraints & Verification Plan

### Automated Tests
- Full test run comparison: Measure test count, pass rate, and execution time before vs after pruning.
- Run `ruff check` and boundary check on test directories.

### Manual Verification
- Review pruned test lists with Jacob to ensure no visionary product contracts are accidentally removed.
