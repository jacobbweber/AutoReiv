# Design

CARD-080 already owns the table. This slice is the convention, the Coding restriction, and prompts.

## Action to route to function

1. Conductor `set_card_status` Ready -> (Coding starts) Ready -> In Progress via Conductor or Coding? Conductor typically sets In Progress on handoff, or Coding does. Coding restriction: if the in-flight agent is `coding`, `set_card_status` only accepts current In Progress -> In Review. Conductor still performs Discuss -> Ready, Ready -> In Progress, and Returned -> In Progress.
2. Coding implements, then `set_card_status` In Progress -> In Review, then stops. Hand off is Conductor's job; Coding may `handoff_to_agent` to conductor/review if asked.
3. Review In Review -> Done | Returned (already allowed).
4. Conductor sees Returned: if rounds < max, `set_card_status` In Progress and `handoff_to_agent` coding. If at max, ask Jacob.

`CardSkill.set_card_status` reads `get_tool_context()["agent_id"]`. No new engine.

## Out of this slice

Projects studio. Git. GitHub issues.
