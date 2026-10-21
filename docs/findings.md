# Findings

One line per finding, under the milestone it belongs to. Search this file and the open cards before adding (skill `card`, dedupe).
Sunday triage turns worthwhile findings into cards and deletes the rest with a reason.

Format: `- YYYY-MM-DD | area | symptom | from CARD-N | suspected files`

## M31 Codebase Tightening, Modularization & Architectural Hygiene

## M32 Projects as user data and development skills

## M33 Domain Skill Consolidation (Wiki & Education) & Real-Project Dogfooding
- 2026-10-21 | web-chat | At 390px phone width, `#agentSelect` (`min-w-[150px]`) inside `#chatEngineSelector` (`min-w-0`) overlaps with `#chatActiveProjectPill` (`shrink-0`) in the Chat top bar when an active project pill is shown | from CARD-740 | `src/web/templates/partials/chat.html`
