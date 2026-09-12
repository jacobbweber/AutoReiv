"""CARD-271: ReAct vs Job spine routing honesty."""
from src.application.orchestration.standing_job_graph import StandingRoute, route_standing_chat


def test_short_chitchat_is_react():
    assert route_standing_chat("hi") == StandingRoute.SHORT_REACT
    assert route_standing_chat("thanks") == StandingRoute.SHORT_REACT
    assert route_standing_chat("what is a job?") == StandingRoute.SHORT_REACT


def test_outcome_shaped_is_job_graph():
    text = (
        "First research the wiki for agent packs, then list open gaps, "
        "then write a short summary note of findings."
    )
    assert route_standing_chat(text) == StandingRoute.MULTI_STEP_JOB_GRAPH
    goal = (
        "Build a complete standing Job proof: create a durable multi-phase outcome "
        "that Observability can open by job_id with journey events."
    )
    assert route_standing_chat(goal) == StandingRoute.MULTI_STEP_JOB_GRAPH
