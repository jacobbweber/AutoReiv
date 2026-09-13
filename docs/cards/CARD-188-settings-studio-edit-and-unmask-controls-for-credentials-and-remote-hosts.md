# [CARD-188] Settings Studio Edit and Unmask Controls for Credentials and Remote Hosts

> **Status**: Done
> **Created**: 2026-09-07
> **Spec Reference**: docs/specs/settings-credentials-and-hosts-edit/
> **Labels**: `type:feature`, `AutoReiv.Web`, `AutoReiv.Security`, `AutoReiv.Settings`

---

## 1. Why / Intent

Operators managing credentials and remote hosts in Settings Studio currently have to delete and recreate entries if they make a typo or want to update a password, port, address, or description. Furthermore, operators cannot unmask or verify the secret value they entered into the vault or review it later without shell access to the database.

Adding edit controls and sensitive field unmasking directly in Settings Studio makes managing keys, tokens, and SSH endpoints convenient and error-resistant.

---

## 2. What to Build

### Beat 1: Credential Vault Edit & Unmask (Settings Studio)
- **Table Controls**:
  - Add an **Edit** button (`[data-edit-cred]`) to each credential row. Clicking populates `#credNameInput`, `#credIdInput` (read-only during edit), `#credTypeSelect`, `#credDescInput`, and opens `#credentialFormContainer`.
  - Add an **Unmask / Eye** button (`[data-reveal-cred]`) next to the masked secret preview (`••••••••`). Clicking invokes `GET /api/vault/credentials/{id}/reveal` and toggles between masked and plaintext display.
- **Form Controls**:
  - Add an eye toggle button (`#toggleCredSecretVisibilityBtn`) inside/beside `#credSecretInput` to toggle between `type="password"` and `type="text"`.
  - Allow saving without re-entering the secret when editing (preserving the existing encrypted secret).
- **Backend Endpoint**:
  - Add `GET /api/vault/credentials/{cred_id}/reveal` endpoint in `src/web/routers/credentials.py` to retrieve the unmasked secret for authorized local operator inspection.

### Beat 2: Remote Hosts Edit (Settings Studio)
- **Table Controls**:
  - Add an **Edit** button (`[data-edit-host]`) to each remote host row.
  - Clicking populates `#hostLabelInput`, `#hostIdInput` (read-only during edit), `#hostAddressInput`, `#hostPortInput`, `#hostAuthTypeSelect`, `#hostUsernameInput`, `#hostCredentialSelect`, and opens `#remoteHostFormContainer`.
- **Form & Backend Handling**:
  - Saving sends `POST /api/remote_hosts` which updates the existing host record by ID.
  - Form resets cleanly on cancel or save.

---

## 3. Acceptance Criteria (Definition of Done)

- [x] [REQ-VAULT-006] REST API endpoint `GET /api/vault/credentials/{cred_id}/reveal` returns the decrypted secret value for operator inspection.
- [x] [REQ-VAULT-007] Settings Studio Credential table provides an Edit button pre-populating the form and allowing secret update or retention.
- [x] [REQ-VAULT-008] Settings Studio Credential table provides an Eye/Unmask toggle revealing the decrypted secret, and the form provides a password/text toggle.
- [x] [REQ-REMOTE-006] Settings Studio Remote Hosts table provides an Edit button pre-populating the form and allowing modification of host parameters.
- [x] Automated frontend unit tests green via `npx vitest run`.
- [x] Automated backend unit tests green via `pytest`.
- [x] Zero lint errors via `ruff check .`.

---

## 4. Constraints & Honor Flags

- Zero third-party product names in card, UI, or repo artifacts.
- Unmasked values only display on explicit operator click; default display remains strictly masked (`••••••••`).
- No changes without operator approval.

