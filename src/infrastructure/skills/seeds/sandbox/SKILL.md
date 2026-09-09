---
name: Isolated Code Sandbox
description: Guarded ephemeral code execution in an isolated sub-process environment.
---

# Isolated Code Sandbox

Use this runbook to execute untrusted, computational, or dynamic scripts inside an isolated subprocess sandbox.

## Tools

- execute_code — execute python or shell code inside an ephemeral guarded subprocess container

## Order

1. Determine script input, target language, and expected stdout/stderr output.
2. Structure execution payloads without side-effects to the parent host environment.
3. Invoke `execute_code` with necessary arguments and timeout boundaries.
4. Parse the structured execution envelope for exit code, stdout, and error metrics.

## When

- Safe execution of mathematical expressions, data parsing scripts, or transient data transforms.
- Running unverified third-party scripts or evaluating code snippets during tasks.

## Pitfalls

- Do not use sandbox execution for operations requiring persistent host daemon services.
- Never hardcode sensitive credentials directly inside sandbox script code strings.

## Done-when

- Code execution completes and returns exit code 0 with captured stdout, or structured error output on failure.
