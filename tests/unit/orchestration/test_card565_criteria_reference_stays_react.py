"""CARD-565: mentioning acceptance/success criteria is not a standing-Job ask; stating them still is."""

import pytest

from src.application.orchestration.standing_job_graph import StandingRoute, route_standing_chat

REFERENCES = [
    "Please review CARD-3 against its acceptance criteria and record your verdict.",
    "Review CARD-3 against its acceptance criteria and record your verdict. Do not hand it back to Developer yet.",
    "Does CARD-12 meet the acceptance criteria listed on the card? Tell me what is missing.",
    "Can you check the card's success criteria for CARD-7 and say whether it is done?",
]
STATED = [
    "Build a small health page for the notes API. Acceptance criteria: GET /health returns 200 and shows the version.",
    "Produce a one-page summary of the wiki gaps, success criteria: every open card is listed with its owner.",
]


@pytest.mark.parametrize("text", REFERENCES)
def test_a_reference_to_criteria_stays_a_normal_turn(text):
    assert route_standing_chat(text) == StandingRoute.SHORT_REACT


@pytest.mark.parametrize("text", STATED)
def test_stated_criteria_still_start_a_standing_job(text):
    assert route_standing_chat(text) == StandingRoute.MULTI_STEP_JOB_GRAPH
