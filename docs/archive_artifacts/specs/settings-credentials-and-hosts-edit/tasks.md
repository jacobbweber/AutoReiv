# Task Breakdown: Settings Studio Edit and Unmask Controls

> **Spec Status**: Complete  
> **Card Reference**: CARD-188  

---

## Tasks

- [x] Task 1: Backend Vault Reveal Endpoint & Retention Logic (`[REQ-VAULT-006]`)
  - [x] Add `GET /api/vault/credentials/{cred_id}/reveal` in `src/web/routers/credentials.py`.
  - [x] Update `POST /api/vault/credentials` in `src/web/routers/credentials.py` to allow retaining existing secret on edit.
  - [x] Unit tests in `tests/unit/web/test_credentials_api.py`.

- [x] Task 2: Frontend HTML Template Controls (`[REQ-VAULT-008]`)
  - [x] Add eye toggle button `#toggleCredSecretVisibilityBtn` in `src/web/templates/index.html`.
  - [x] Ensure proper icon and aria attributes.

- [x] Task 3: Settings Studio JS Wiring (`[REQ-VAULT-007]`, `[REQ-VAULT-008]`, `[REQ-REMOTE-006]`)
  - [x] Wire `[data-reveal-cred]` secret reveal toggle in `settings.js`.
  - [x] Wire `[data-edit-cred]` credential editing flow in `settings.js`.
  - [x] Wire `#toggleCredSecretVisibilityBtn` form secret input visibility in `settings.js`.
  - [x] Wire `[data-edit-host]` remote host editing flow in `settings.js`.

- [x] Task 4: Automated Tests & Verification
  - [x] Frontend unit tests in `tests/unit/frontend/settings_edit_unmask.test.js`.
  - [x] Pytest suite and Vitest suite execution.
