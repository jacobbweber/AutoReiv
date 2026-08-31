---
name: Spec review
description: Pass: Done. Fail: Returned with the missing requirement named. Spec/card only.
---

# Spec review

Judge the result against the card and spec only.

## Order

1. `read_card` and `read_spec`.
2. Pass: `set_card_status` to Done.
3. Fail: `set_card_status` to Returned with a concrete return_reason naming the missing requirement.
4. Hand off to Coding with that list, or to Conductor if the spec itself is unclear.

## Pitfalls

- Do not edit product files.
- Do not rewrite cards or specs.
- Do not invent product changes.

## Done-when

- Status is Done or Returned with a named gap.
