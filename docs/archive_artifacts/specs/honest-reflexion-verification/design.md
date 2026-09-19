# Design

Theater today: no `verifier_tool_name` short-circuits to verified, and chat always emits `passed: true`.

New path:

1. Run the agent turn.
2. If a verifier tool is named, execute it (existing).
3. Else if `use_builtin_critic` (chat self_verify), call `gateway.complete` with a JSON-only critic prompt. Parse `{is_valid, discrepancies}`. Invalid JSON = fail.
4. Else status=`skipped`, `verification_passed=false`.
5. On fail, retry with the critique appended, up to `max_refinements`.

Chat maps `turn_res.verification_passed` onto the SSE payload. No green badge unless `passed` is true.
