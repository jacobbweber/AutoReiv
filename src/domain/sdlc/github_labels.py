"""
Card status / type -> GitHub issue labels [REQ-SDLC-040, REQ-SDLC-041].
"""

from typing import List

from src.domain.sdlc.models import normalize_status

STATUS_TO_LABEL = {
    "Discuss": "status:discuss",
    "Ready": "status:ready",
    "In Progress": "status:in-progress",
    "In Review": "status:in-review",
    "Returned": "status:returned",
    "Done": "status:done",
}


def github_label_map(status: str, labels_line: str = "") -> List[str]:
    labels: List[str] = []
    mapped = STATUS_TO_LABEL.get(normalize_status(status))
    if mapped:
        labels.append(mapped)
    for part in (labels_line or "").replace("`", "").split(","):
        token = part.strip()
        if token.startswith("type:"):
            labels.append(token)
    return labels
