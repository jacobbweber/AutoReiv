# CARD-317 CHANGELOG snippet

Fold into `CHANGELOG.md` [Unreleased] ### Added:

- CARD-317: Education Priming write-back — Ask Priming / `priming_writeback` lands Wiki schema/outline note (catalog `wiki_note_*` only) **and** `memory.db` ledger anchors (`education_mastery` + learner `priming_topic`); unregistered/forbidden wiki tools soft-fail without blocking note write-back (`tests/unit/education/test_card317_priming_writeback.py`)
