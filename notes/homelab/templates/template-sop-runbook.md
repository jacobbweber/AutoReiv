---
doc_type: template
owner_role: homelab-admin
scope: operations
last_verified: "2026-09-09"
status: template
---

# Template: Standard Operating Procedure (SOP / Runbook)

Use this template when authoring operational runbooks in `notes/homelab/50-runbooks/`.

## 1. Scope & Objective
- **Target Systems**: `[List of systems affected]`
- **Objective**: `[What this SOP achieves]`
- **Estimated Execution Time**: `[e.g., 15 minutes]`

## 2. Prerequisites & Pre-Flight Checks
- [ ] Safety checkpoint / snapshot taken if mutating state.
- [ ] Required credentials available from Credential Vault.
- [ ] Target systems reachable on network.

## 3. Step-by-Step Procedure
1. Step 1: `[Description and exact commands]`
   ```bash
   # Execution command
   ```
2. Step 2: `[Description and verification]`

## 4. Verification & Health Check
- [ ] `[Command or metric check confirming success]`

## 5. Rollback Procedure
1. `[Step to revert changes if verification fails]`
