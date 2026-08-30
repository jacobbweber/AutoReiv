---
name: okta-admin
description: Homelab Okta admin playbook. Directory, groups, apps, and MFA SOP. No live Okta API.
---

# Okta Admin (homelab)

Operate Okta as an admin using this playbook. Declared tools are **stubs**.
They do not call Okta and do not read API tokens. Open this pack in Skills Studio.

**Compatibility:** live Okta tools are not wired. Invoking a declared tool does not
perform HTTP and does not require Okta environment variables. AutoReiv boots
without any Okta credentials. Do not treat these names as a working integration.

## When to use

- Find a homelab user by login or email
- List groups and confirm membership with the human
- Reset or unlock a user, including MFA, as a conceptual SOP only
- Assign an application to a person or group
- Check MFA enrollment status with the human before any change

## Playbook steps

Confirm the actor, the target, and the change with the human before every step.
Do not invent live API calls. Do not log secrets.

### 1. List users

1. Ask the human for a login, email, or name fragment.
2. Call `okta_list_users` with `query` set to that fragment (stub; no directory call).
3. Read back the stub result honestly. Ask the human to confirm the person from their own Okta admin view if needed.

### 2. Groups

1. Identify the group name or id with the human.
2. Call `okta_list_groups` with `query` set to that fragment (stub).
3. Confirm membership changes with the human. Do not assume a write succeeded.

### 3. Reset MFA / unlock (conceptual)

1. Identify the user (login or email) and the intended action: unlock, or reset MFA factors.
2. Confirm the human is looking at the same person in the Okta admin console.
3. Call `okta_reset_or_unlock` with `login` and `action` (`unlock` or `reset_mfa`) (stub).
4. Tell the human the live MFA reset is not performed by AutoReiv. They complete it in Okta if they still want it.

### 4. Assign an application

1. Confirm the application label and the target user or group.
2. Call `okta_assign_app` with `app` and `target` (stub).
3. Ask the human to verify assignment in Okta. The stub did not change the tenant.

## Pitfalls

- Never log API tokens, SSWS headers, OAuth client secrets, or refresh tokens.
- Never paste tokens into chat, SKILL.md, or tool arguments.
- Never add Okta env keys to `.env` for this pack; they are not required to boot.
- A stub error means the tool is a playbook declaration, not a failed HTTP call.

## Declared tools (stubs)

```json
{
  "name": "okta_list_users",
  "description": "Stub: list Okta users by login or email. Not wired to the Okta API.",
  "parameters": {
    "type": "object",
    "properties": {
      "query": {"type": "string", "description": "Login, email, or name fragment"}
    }
  }
}
```

```json
{
  "name": "okta_reset_or_unlock",
  "description": "Stub: unlock a user or reset MFA factors. Not wired to the Okta API.",
  "parameters": {
    "type": "object",
    "properties": {
      "login": {"type": "string", "description": "User login or email"},
      "action": {"type": "string", "description": "unlock or reset_mfa"}
    },
    "required": ["login", "action"]
  }
}
```

```json
{
  "name": "okta_assign_app",
  "description": "Stub: assign an application to a user or group. Not wired to the Okta API.",
  "parameters": {
    "type": "object",
    "properties": {
      "app": {"type": "string", "description": "Application label or id"},
      "target": {"type": "string", "description": "User login or group name"}
    },
    "required": ["app", "target"]
  }
}
```

```json
{
  "name": "okta_list_groups",
  "description": "Stub: list Okta groups by name. Not wired to the Okta API.",
  "parameters": {
    "type": "object",
    "properties": {
      "query": {"type": "string", "description": "Group name fragment"}
    }
  }
}
```
