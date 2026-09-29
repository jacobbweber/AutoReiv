"""CARD-583: quiz extraction reads the shipped education-quiz template's Prompt / Expected Binary Answer items."""

from __future__ import annotations

from src.application.education.quiz_engine import extract_quiz_items_from_note
from src.application.education.templates import EDUCATION_TEMPLATES

TUTOR_NOTE = """# Kubernetes basics

Kubernetes schedules containers into Pods on Nodes.

## Key facts
- etcd stores cluster state.

## Quiz
### Item 1
- **Prompt:** What is the smallest deployable unit in Kubernetes?
- **Expected Binary Answer:** Pod
- **Mastery Item ID:** auto

### Item 2
- **Prompt:** Which control-plane component stores cluster state as a key-value store?
- **Expected Binary Answer:** etcd
- **Mastery Item ID:** auto
"""


def test_template_style_items_are_extracted():
    items = extract_quiz_items_from_note(TUTOR_NOTE, wiki_path="01_Notes/kubernetes-basics.md", topic="k8s")
    assert [(i["prompt"], i["expected_answer"]) for i in items] == [
        ("What is the smallest deployable unit in Kubernetes?", "Pod"),
        ("Which control-plane component stores cluster state as a key-value store?", "etcd"),
    ]


def test_unfilled_template_placeholders_are_not_items():
    tpl = EDUCATION_TEMPLATES["education-quiz"]
    assert "**Prompt:**" in tpl["content"]
    assert extract_quiz_items_from_note(tpl["content"], wiki_path="t.md") == []


def test_plain_prompt_and_expected_answer_without_bold():
    note = "## Quiz\n- Prompt: What talks to the API server?\n- Expected Answer: kubectl\n"
    items = extract_quiz_items_from_note(note, wiki_path="n.md")
    assert [(i["prompt"], i["expected_answer"]) for i in items] == [("What talks to the API server?", "kubectl")]


def test_q_a_bullets_still_work():
    note = "## Quiz\n- Q: What stores cluster state?\n  A: etcd\n"
    items = extract_quiz_items_from_note(note, wiki_path="n.md")
    assert [(i["prompt"], i["expected_answer"]) for i in items] == [("What stores cluster state?", "etcd")]
