# Requirements Specification: Settings Studio Edit and Unmask Controls

> **Spec Status**: In Progress  
> **Card Reference**: CARD-188  
> **Primary Component**: `AutoReiv.Web`, `AutoReiv.Security`, `AutoReiv.Settings`  
> **Applicable ADRs**: `docs/adr/0003-agent-kernel-scoped-tool-registry-and-sqlite-state-persistence.md`

---

## 1. Executive Summary & Intent

Operators managing secrets and remote SSH endpoints in Settings Studio require the ability to update configuration details (labels, hosts, ports, descriptions, or secrets) without having to delete and recreate them. Furthermore, operators need to be able to unmask and inspect sensitive values (passwords, API tokens, and SSH keys) directly in Settings Studio to verify correctness.

---

## 2. User Stories & EARS Functional Requirements

### [REQ-VAULT-006]: Operator Credential Secret Reveal Endpoint
- **Type**: Event-Driven
- **EARS Statement**: `WHEN an operator requests to inspect a stored credential THE SYSTEM SHALL return the decrypted secret value via GET /api/vault/credentials/{cred_id}/reveal.`
- **Acceptance Criteria**:
  - [ ] Given a valid `cred_id`, when `GET /api/vault/credentials/{cred_id}/reveal` is called, then the decrypted secret is returned as `{ "id": cred_id, "secret": decrypted_secret }`.
  - [ ] Given an unknown `cred_id`, when the reveal endpoint is called, then a 404 error is returned.

### [REQ-VAULT-007]: Settings Studio Credential Edit Flow
- **Type**: Event-Driven
- **EARS Statement**: `WHEN an operator clicks the Edit button on a credential row THE SYSTEM SHALL populate the credential form and allow updating metadata and secret.`
- **Acceptance Criteria**:
  - [ ] Given an existing credential, when the Edit button is clicked, then the form opens populated with name, ID (read-only), type, and description.
  - [ ] Given an edit submission with an empty secret field, when saved, then the existing encrypted secret is preserved.
  - [ ] Given an edit submission with a new secret, when saved, then the new secret is encrypted and stored.

### [REQ-VAULT-008]: Settings Studio Sensitive Field Unmask Controls
- **Type**: Event-Driven
- **EARS Statement**: `WHEN an operator clicks an unmask toggle button THE SYSTEM SHALL switch the display between masked dots and cleartext.`
- **Acceptance Criteria**:
  - [ ] Given a credential row in Settings Studio, when clicking the eye icon next to the masked preview, then the decrypted secret is displayed in place of the masked dots.
  - [ ] Given the credential secret input field, when clicking the visibility toggle button, then the input type toggles between `password` and `text`.

### [REQ-REMOTE-006]: Settings Studio Remote Host Edit Flow
- **Type**: Event-Driven
- **EARS Statement**: `WHEN an operator clicks the Edit button on a remote host row THE SYSTEM SHALL populate the remote host form and update the existing host record upon save.`
- **Acceptance Criteria**:
  - [ ] Given an existing remote host, when the Edit button is clicked, then the form opens populated with label, host ID (read-only), address, port, auth type, username, and linked credential ID.
  - [ ] Given an edit submission, when saved, then `POST /api/remote_hosts` updates the existing host record with the modified fields.
