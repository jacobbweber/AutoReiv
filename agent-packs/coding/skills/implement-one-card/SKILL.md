---
name: Implement one card
description: Read card/spec, write the deliverable, commit if repo, In Review, stop.
---

# Implement one card

Implement exactly one Ready card against its spec. Then stop.

## Order

1. First tool call is `read_card` or `read_spec`.
2. Write the card's primary deliverable with `write_project_file`.
3. `git_status`. If there is no repo, skip `git_commit`. Otherwise conventional `git_commit`.
4. `set_card_status` from In Progress to In Review only.
5. Stop. Do not mark Done or Returned. Do not start another card.

## Pitfalls

- Do not return a prose plan as the whole turn.
- Do not claim done if the deliverable file is not written.
- Do not use `cli_exec`. Platform SRE is AutoReiv.
- Do not tick a next card.

## Done-when

- Deliverable is on disk.
- Commit exists if the project is a repo.
- Card is In Review.
