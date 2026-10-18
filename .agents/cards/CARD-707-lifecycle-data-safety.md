---
id: CARD-707
title: "Fix reboot skill-pruning data loss, Vault key persistence & path resolution, fail-closed tool checks, and online SQLite backup snapshots"
type: bug
status: In Review
priority: P1
milestone: M31
needs_decision: none
proof:
  journeys: [card-707-lifecycle-data-safety]
  checks: [tests/unit/infrastructure/test_card707_lifecycle_data_safety.py]
branch: feat/card-707-lifecycle-data-safety
log: {minutes: 12, qa_runs: 2, findings: 0}
created: 2026-10-17
---

# CARD-707 Fix reboot skill-pruning data loss, Vault key persistence & path resolution, fail-closed tool checks, and online SQLite backup snapshots

## Problem
1. **Reboot data loss on user skill customizations**: `prune_bled_platform_skills()` in `src/infrastructure/data/resolver.py:556-590` lists `"platform-health"` and `"session-inspect"` in `BLED_AGENT_SKILL_IDS`. Both are active shipped skills under `platform/skills/`. When an operator edits either skill in Capabilities Studio, the user copy is saved to `$DATA_DIR/skills/<id>/SKILL.md` (ADR-0062). On the next server restart, `bootstrap_data_dir()` runs `prune_bled_platform_skills()`, which unconditionally `shutil.rmtree()`s `$DATA_DIR/skills/platform-health` and `$DATA_DIR/skills/session-inspect`, wiping out the user's changes.
2. **CredentialVault wrong fallback path and silent ephemeral key on write failure**: `CredentialVault.__init__` in `src/domain/security/vault.py:46-60` hardcodes `Path(os.getenv("AUTOREIV_DATA_DIR") or Path.home() / ".autoreiv")` instead of resolving via `DataDirResolver().resolve().root`, violating `.agents/rules/boundaries.md`. Worse, if writing `.vault_key` fails, `except Exception: pass` swallows the error and keeps an ephemeral in-memory key, encrypting secrets into SQLite that become permanently undecryptable on the next process restart.
3. **Fail-open permission check in `is_known_tool()`**: `src/infrastructure/content/store.py:474-481` returns `True` when `_TOOL_REGISTRY is None` or when `_TOOL_REGISTRY.get_tool_definition(name)` raises an exception, violating ADR-0061 ("an unknown tool id grants nothing").
4. **Unsafe WAL SQLite snapshot in `UpdateService`**: `UpdateService._snapshot_database()` in `src/application/system/update_service.py:914-938` copies the live WAL-mode `autoreiv.db` with `shutil.copy2` without checkpointing or using `sqlite3.Connection.backup()`, risking a truncated/inconsistent snapshot if uncommitted WAL frames exist.

## Cause
- `"platform-health"` and `"session-inspect"` were mistakenly added to `BLED_AGENT_SKILL_IDS` alongside `.agents/skills/` dev skills (`preflight`, `live-qa`, `card`, etc.), without checking if a skill ID is a legitimate shipped platform skill under `platform/skills/`.
- `CredentialVault` was written before `DataDirResolver` was standardized and swallowed I/O errors during key generation.
- `is_known_tool()` returned `True` in its exception branch.
- `UpdateService._snapshot_database()` bypassed `sqlite3.Connection.backup()`.

## Change
- Remove `"platform-health"` and `"session-inspect"` from `BLED_AGENT_SKILL_IDS` in `src/infrastructure/data/resolver.py`, and guard `prune_bled_platform_skills()` so it never deletes any directory whose ID exists in shipped `platform/skills/`.
- Update `CredentialVault` (`src/domain/security/vault.py`) to resolve its default directory via `DataDirResolver().resolve().root` and raise an `OSError` if persisting a newly generated `.vault_key` fails (only ignoring `chmod` on platforms/filesystems where POSIX permissions are unsupported).
- Change `is_known_tool()` in `src/infrastructure/content/store.py` to fail closed (`return False`) when `_TOOL_REGISTRY.get_tool_definition(name)` raises an exception.
- Update `UpdateService._snapshot_database()` in `src/application/system/update_service.py` to use SQLite's online backup API (`src_conn.backup(dst_conn)`) instead of `shutil.copy2`.

## What dies
- `"platform-health"` and `"session-inspect"` entries in `BLED_AGENT_SKILL_IDS` (`src/infrastructure/data/resolver.py`).
- Hardcoded `Path.home() / ".autoreiv"` fallback and silent key-write `except Exception: pass` in `src/domain/security/vault.py`.
- Raw `shutil.copy2` database snapshot in `src/application/system/update_service.py`.

## Proof
- Journey `card-707-lifecycle-data-safety`:
  1. Customize `platform-health` in Capabilities Studio (`PUT /api/capabilities/skills/platform-health/file`), verify the user override is saved and survives `prune_bled_platform_skills()`, and verify Capabilities Studio displays the customized skill on desktop and phone.
  2. Save and verify an encrypted credential in Settings > Credential Vault (`/api/vault/credentials`), confirming `.vault_key` lives under the resolved data root and the masked credential renders in `#vaultCredentialsList`.
- Checks:
  - `tests/unit/infrastructure/test_card707_lifecycle_data_safety.py`

## Plan and decisions
- Technical bug fixes under Phase 1 (Option 1 approved by Jacob).

## Findings
- None.

## Results
| Journey / Check | Viewport | Result | Notes |
|---|---|---|---|
| `preflight.py --fast --base qa` | — | PASS (GREEN) | ruff PASS, eslint PASS, pytest guard 262 passed, changed tests 4 passed, mapped tests 165 passed, vitest 1124 passed |
| `card-707-lifecycle-data-safety` | desktop | PASS | User override of `platform-health` saved and rendered in `#view-capabilities`; encrypted Vault credential saved via `/api/vault/credentials` and rendered in `#vaultCredentialsList` |
| `card-707-lifecycle-data-safety` | phone | PASS | Same verified on mobile viewport |

Screenshots:
- `/tmp/autoreiv-qa/card-707/card-707-lifecycle-data-safety-desktop-01-save-user-customization-of-shipped-platform-heal.png`
- `/tmp/autoreiv-qa/card-707/card-707-lifecycle-data-safety-desktop-02-save-encrypted-credential-in-credential-vault-an.png`
- `/tmp/autoreiv-qa/card-707/card-707-lifecycle-data-safety-phone-02-save-encrypted-credential-in-credential-vault-an.png`

## Release note
- Fixed startup skill pruning deleting user copies of `platform-health` and `session-inspect`, hardened `CredentialVault` key persistence under the data root, made `is_known_tool` fail closed on errors, and switched pre-update DB snapshots to SQLite online backup [CARD-707].
