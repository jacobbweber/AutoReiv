---
name: regression-sentinel
description: >-
  Standardized protocol for authoring negative assertion regression tests. Use when fixing bugs or regressions to ensure they can never quietly recur.
---

# Regression Sentinel (Negative Assertion & Bug Lock Protocol)

> **For Jacob (Plain Language)**: When we fix a bug, it's not enough to just write code that seems to work today. We must lock in a permanent automated test with a **negative assertion**—a specific check that asserts what the software MUST NOT do (e.g. "assert the server does NOT wipe custom tools on reboot", "assert the wiki does NOT create folders in the repo root"). This acts as an automated tripwire that sounds an alarm if the bug ever tries to come back.

---

## When to Run This Skill

- Whenever addressing a bug card (e.g. CARD-381, CARD-382).
- Before fixing any unexpected regression or reported defect.
- Whenever Jacob asks: _"Run regression sentinel for `<bug/card>`"_.

---

## The 4-Step Bug Lock Protocol

### Step 1: Write the Failing Negative Assertion Test (Red Phase)

Before touching any production code, write a test that reproduces the bug:

- Formulate the assertion as a **negative invariant** or **boundary guard**:
  - `assert "custom_mcp_tool" in agent.tools` (verifying it wasn't dropped)
  - `assert not (repo_root / "00_Inbox").exists()` (verifying stray directory wasn't created)
  - `assert not (repo_root / "autoreiv.db").exists()` (verifying checkout wasn't polluted)
- Reference the card ID in the docstring:

  ```python
  def test_reboot_does_not_wipe_custom_tools_card_381(test_env):
      """CARD-381: Verify factory pack reconciliation never clobbers operator tools."""
      ...
  ```

- Run the test and confirm it fails for the exact reason reported.

### Step 2: Implement the Minimal Fix (Green Phase)

1. Make the smallest architectural change necessary to resolve the root cause.
2. Re-run the test to confirm it transitions from Red to Green.
3. Verify that all existing unit and integration tests remain passing.

### Step 3: Run the Scavenger Pass

1. Use `grep_search` to check for any dead symbols or orphaned callers left behind by the fix.
2. Remove any temporary test fixtures or scratch files.
3. Run `ruff check .` and `npm run lint:frontend`.

### Step 4: Add to Preflight Gate

Confirm the new test is automatically executed by the unified preflight runner:

```bash
npm run preflight
# or: pytest tests/unit/ -k "card_381"
```
