"""CARD-649: the lab grader passed a criterion as soon as any one of its words appeared in the
submission, so a sentence that drops one term per criterion passed the whole lab. A criterion now
needs meaningful coverage: about half of its key terms (at least two when it has two or more),
matched generously across word forms. Pasting the criteria back is not a submission either."""

from __future__ import annotations

from src.application.education.labs import grade_lab_submission

CRITERIA = [
    "Follower rejects entries when the previous index and term do not match",
    "Commit index advances only after a majority stored the entry",
]
REAL = (
    "My Raft lab: the leader keeps entries with index and term. A follower rejects AppendEntries when the previous "
    "index and term do not match, and the leader advances the commit index after a majority stored the entry."
)


def _grade(submission: str, criteria=CRITERIA):
    return grade_lab_submission(topic="Raft log replication", submission=submission, expected_invariants=criteria)


def test_one_word_per_criterion_no_longer_passes():
    res = _grade("I studied how a follower behaves and the commit stuff from my notes today, nothing more to add.")
    assert res["passed"] is False
    assert set(res["failed_invariants"]) == set(CRITERIA)


def test_repeating_terms_does_not_pass():
    res = _grade("follower follower follower follower commit commit commit commit majority majority majority")
    assert res["passed"] is False


def test_pasting_the_criteria_back_is_not_a_submission():
    res = _grade(". ".join(CRITERIA) + ".")
    assert res["passed"] is False
    assert "own words" in res["feedback"]


def test_a_real_submission_passes_generously_across_word_forms():
    assert _grade(REAL)["passed"] is True
    # Different word forms and order still count (rejected/rejects, stores/stored, matching/match).
    reworded = (
        "In my model the follower rejected new entries whenever the term at the previous index was not matching its own "
        "log. The leader only advanced the commit index once a majority of servers stores the entry."
    )
    assert _grade(reworded)["passed"] is True


def test_a_criterion_with_thin_coverage_fails_and_says_what_is_missing():
    thin = (
        "My Raft lab: a follower rejects new entries when the previous index and term do not match its log, so the "
        "leader retries earlier. I did not get to the commit part."
    )
    res = _grade(thin)
    assert res["passed"] is False
    assert res["passed_invariants"] == [CRITERIA[0]]
    assert res["failed_invariants"] == [CRITERIA[1]]
    assert "majority" in res["feedback"]


def test_single_term_criterion_needs_that_term():
    crit = ["Heartbeats"]
    ok = "The leader sends heartbeats on a timer so followers do not start an election while it is alive."
    assert _grade(ok, crit)["passed"] is True
    assert _grade("The leader sends periodic messages so that followers stay quiet while it lives.", crit)["passed"] is False


# Follow-up from the course-filler-3 live check: Spark phrases criteria as "The response states ..." and
# adds negative checks ("The response does not mention acceptance when the term check fails"). Rubric
# words are not topic terms, and a "does not" criterion cannot be shown by covering its words.
SPARK_CRITERIA = [
    "The response states the follower's log term at the previous index differs from the leader's term.",
    "The response states the follower rejects the AppendEntries message.",
    "The response states the leader retries with an earlier index after rejection.",
    "The response does not mention acceptance when the term check fails.",
]
LIVE_SUBMISSION = (
    "My Raft log replication lab: the leader appends each client command to its log with the current term and sends "
    "AppendEntries with the previous log index and term to every follower. A follower rejects entries when its log has "
    "no entry at the previous index with the same term, and the leader retries with an earlier index."
)


def test_rubric_words_and_negative_checks_do_not_fail_a_real_submission():
    res = _grade(LIVE_SUBMISSION, SPARK_CRITERIA)
    assert res["passed"] is True, res["feedback"]


def test_rubric_phrased_criteria_still_need_their_topic_terms():
    res = _grade("My lab response states things and mentions the response clearly, as the response should state.", SPARK_CRITERIA)
    assert res["passed"] is False
