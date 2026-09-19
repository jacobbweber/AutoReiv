---
name: lifecycle-audit
description: >-
  Audits state persistence, reconciliation, and survival across server reboots. Use to verify that user changes (agents, tools, settings, routines) survive restarts without getting clobbered by factory defaults.
---

# Lifecycle Audit (Reboot & Persistence Integrity)

> **For Jacob (Plain Language)**: When you change something in AutoReiv (like enabling MCP tools, tweaking an agent's prompt, or configuring a model), that change must stay saved even if you restart the server or reboot your PC. This audit verifies that our startup code doesn't accidentally overwrite your custom settings with factory defaults.

---

## When to Run This Audit

- After adding or modifying agent configuration, MCP tools, routines, or provider settings.
- Before declaring any card `In Review` that touches persistence, database models, or factory pack reconciliation.
- Whenever Jacob asks: _"Run lifecycle audit on `<feature>`"_.

---

## The 5-Step Verification Protocol

### Step 1: Baseline & Mutate State

1. Apply a specific state change via the UI or REST API (e.g. enable an MCP tool on an agent).
2. Inspect the database and filesystem to verify the write occurred in user data:
   - Check SQLite: `python -c "import sqlite3; ..."`
   - Check JSON pack file in `$LOCALAPPDATA\AutoReiv\packs\<agent_id>\pack.json`.

### Step 2: Identify Boot Reconciliation Logic

Search for code executed during application startup (`lifespan` in `src/web/app.py` or `src/infrastructure/skills/platform_packs.py`):

```bash
# Locate startup pack sync logic
git grep -n "install_platform_agent_packs" src/
git grep -n "lifespan" src/web/
```

### Step 3: Simulate Server Restart

Execute a clean restart using the serve-hygiene script:

```powershell
uv run python scripts/restart_serve.py --port 8000 --host 127.0.0.1
```

### Step 4: Verify Post-Boot Survival (The Anti-Clobber Gate)

Re-fetch the entity via GET endpoint or inspect the database:

1. **State Preservation**: Ensure the modified fields retain their custom values.
2. **No Blind Overwrite**: Confirm factory re-seeding only added missing defaults and did not clobber user mutations.
3. **No Phantom State**: Verify the UI reflects the persisted state upon fresh page load (Ctrl+F5).

### Step 5: Author a Lifecycle Regression Test

Add a permanent test asserting reboot survival:

```python
def test_user_customization_survives_factory_reseed(pack_service, agent_repo):
    # 1. Seed initial factory pack
    # 2. Operator customizes state (e.g. adds custom tool)
    # 3. Trigger factory pack reinstall / reseed
    # 4. Assert custom tool is STILL present in agent.allowed_tool_names
```
