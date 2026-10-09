"""Does a reply admit that a tool or capability is missing? [CARD-663]

One matcher shared by the capability-gap detector (files the gap) and the reply rules (adds the Ask Developer
line), so the two cannot drift again (CARD-615 gave the line its own pattern and the detector missed wordings such
as "I do not have a direct email-sending tool").

The check is structural, per sentence, not a list of phrases:
- the speaker cannot have / reach a tool: a negated possession verb ("do not have", "lack") or an inability to
  reach one ("cannot access / use / find") with a tool word (tool, capability, integration, ability, function,
  permission) nearby;
- a tool is said not to exist: "there is no fax tool", "no tool is available to ...";
- a tool is said to be unavailable: "the PDF export tool isn't available";
- an action cannot be done directly or without a tool: "I cannot directly create VMs", "... without a tool";
- no agent covers it: "No agent covers faxing notes" (the CARD-615 turn-down, CARD-677).
Questions, conditionals ("If you don't have ...") and sentences about the user ("you don't have ...") never count.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Collection, Optional

_TOOL_NOUN = r"(?:tools?|capabilit(?:y|ies)|abilit(?:y|ies)|integrations?|functions?|permissions?)"

# "tool calls", "tool output": the tool word is a modifier here, not the missing thing.
_NOT_A_TOOL = r"(?!\s+(?:calls?|output|results?|use|usage|errors?|runs?|invocations?|responses?)\b)"
# "no tools were needed", "no write tools will be used", "no tools that change state will be called" [CARD-684]:
# says which tools are (not) used; nothing is missing.
_BE_USED = (
    r"(?:was|were|is|are|will be|would be|will ever be|is being|are being|has been|have been|had been|"
    r"need to be|needs to be|get|gets|got)\s+(?:needed|used|required|necessary|called|involved|run|invoked|executed)\b"
)
_NOT_NEEDED = re.compile(rf"^\s*(?:(?:that|which)\b[^.!?\n]{{0,60}}?\s)?{_BE_USED}", re.IGNORECASE)

_SENTENCES = re.compile(r"(?<=[.!?])\s+|\n+|;\s+|:\s+(?=[A-Z*`_])")
_MARKUP = re.compile(r"[*_`]+")
_NOT_ABOUT_SPEAKER = re.compile(
    r"^\s*(?:if|when|whenever|unless|once|in case)\b|\byou\s+(?:do not|don't|does not|doesn't|cannot|can't|lack|are unable)\b",
    re.IGNORECASE,
)

_HAVE_VERB = r"(?:have|has|possess|own|get)"
_NEG_HAVE = (
    rf"(?:(?:do not|don't|does not|doesn't|did not|didn't|no longer|have not|haven't|has not|hasn't)\s+{_HAVE_VERB}"
    r"|lack(?:s|ing)?|am missing|is missing|are missing)"
)
_CANNOT = r"(?:cannot|can not|can't|am unable to|is unable to|are unable to|unable to|am not able to|not able to)"
_REACH_VERB = r"(?:access|use|find|call|run|reach|see)"

_PATTERNS = (
    # "I do not have a direct email-sending tool", "I lack a tool for ...", "does not have a Slack posting tool"
    re.compile(rf"\b{_NEG_HAVE}\s+(?:access to\s+)?(?P<body>[^.!?\n]{{0,60}}?\b{_TOOL_NOUN}\b(?P<tail>[^.!?\n]*))", re.IGNORECASE),
    # "I can't access a tool that sends SMS", "unable to use any tool that can query DNS"
    re.compile(rf"\b{_CANNOT}\s+(?:{_HAVE_VERB}|{_REACH_VERB})\s+(?P<body>[^.!?\n]{{0,60}}?\b{_TOOL_NOUN}\b(?P<tail>[^.!?\n]*))", re.IGNORECASE),
    # "there is no fax tool", "no tool is available to restart the service"
    re.compile(rf"\b(?P<there>there\s+(?:is|are|'s)\s+|there's\s+)?no\s+(?P<body>(?:[\w-]+\s+){{0,3}}?{_TOOL_NOUN}\b{_NOT_A_TOOL}(?P<tail>[^.!?\n]*))", re.IGNORECASE),
    # "the PDF export tool isn't available to me"
    re.compile(rf"\b(?P<body>(?:[\w-]+\s+){{0,3}}?{_TOOL_NOUN}){_NOT_A_TOOL}\s+(?:is not|isn't|are not|aren't|is no longer)\s+(?:available|offered|enabled|provided)\b(?P<tail>[^.!?\n]*)", re.IGNORECASE),
    # "I cannot directly create virtual machines"
    re.compile(rf"\b{_CANNOT}\s+directly\s+(?P<action>[^.!?\n]+)", re.IGNORECASE),
    # "I'm unable to reboot servers without a tool"
    re.compile(rf"\b{_CANNOT}\s+(?P<action>[^.!?\n]+?)\s+without\s+(?:a|an|any|the)\s+{_TOOL_NOUN}\b", re.IGNORECASE),
    # CARD-677: the turn-down "No agent covers faxing notes" (the CARD-615 wording) names what is missing
    re.compile(r"\bno\s+(?:other\s+)?agents?\b[^.!?\n]{0,40}?\bcovers?\s+(?P<action>[^.!?\n]+)", re.IGNORECASE),
)

# Words in front of "tool" that say nothing about what the tool does.
_FILLER = {
    "a", "an", "any", "the", "such", "that", "this", "direct", "dedicated", "specific", "built-in", "builtin",
    "native", "suitable", "appropriate", "proper", "real", "actual", "available", "relevant", "necessary", "needed",
    "required", "my", "our", "its", "own", "single", "other", "separate", "special", "particular",
}
# A "no ..." phrase whose words are these is not naming a tool ("no problem with the tool").
_STOP = {"with", "of", "in", "on", "about", "from", "by", "at", "and", "or", "but", "to", "for", "is", "was", "be"}
_TAIL_PURPOSE = re.compile(r"^\s*(?:(?:is|are|was|were)\s+)?(?:available\s+)?(?:to|for|that(?:\s+(?:can|could|would|will))?|which(?:\s+can)?)\s+(.+)$", re.IGNORECASE)
# "available to me": the words after "to" name who, not what.
_WHO = {"me", "us", "you", "him", "her", "them", "this agent", "the agent", "agents", "this session", "that", "this", "it"}
_TAIL_CUT = re.compile(r"\s*(?:,|\bso\b|\bbut\b|\bbecause\b|\bin (?:my|this|the)\b|\bavailable\b|\bhere\b|\bright now\b).*$", re.IGNORECASE)


@dataclass(frozen=True)
class MissingTool:
    sentence: str
    capability: str


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", _MARKUP.sub("", text or "")).strip(" .,:;-")


def _capability(body: str, tail: str) -> str:
    purpose = _TAIL_PURPOSE.match(tail or "")
    if purpose:
        found = _clean(_TAIL_CUT.sub("", purpose.group(1)))
        if len(found) >= 2 and found.lower() not in _WHO:
            return found[:80]
    words = re.sub(rf"\b{_TOOL_NOUN}\b.*$", "", body, flags=re.IGNORECASE).split()
    kept = [w for w in words if w.lower().strip("`*_") not in _FILLER]
    found = _clean(" ".join(kept)).replace("-", " ")
    return found[:80]


def _is_tool_phrase(body: str) -> bool:
    words = re.sub(rf"\b{_TOOL_NOUN}\b.*$", "", body, flags=re.IGNORECASE).lower().split()
    return not any(w in _STOP for w in words)


def _says_none_exists(there: Optional[str], body: str, tail: str) -> bool:
    """'no ... tool' admits a gap only when it says no such tool exists, not that none was needed."""
    if _NOT_NEEDED.match(tail):
        return False
    if there or _TAIL_PURPOSE.match(tail):
        return True
    words = re.sub(rf"\b{_TOOL_NOUN}\b.*$", "", body, flags=re.IGNORECASE).split()
    return any(w.lower() not in _FILLER for w in words)


def find_missing_tool(text: Optional[str]) -> Optional[MissingTool]:
    """The first sentence admitting a missing tool and what the tool would do, else None."""
    for raw in _SENTENCES.split(text or ""):
        sentence = raw.strip()
        if not sentence or sentence.rstrip("*_` ").endswith("?"):
            continue
        plain = _MARKUP.sub("", sentence)
        if _NOT_ABOUT_SPEAKER.search(plain):
            continue
        for index, pattern in enumerate(_PATTERNS):
            match = pattern.search(plain)
            if not match:
                continue
            groups = match.groupdict()
            if groups.get("action") is not None:
                capability = _clean(_TAIL_CUT.sub("", groups["action"]))
                if capability.lower() in _WHO:  # "no agent covers that": the prompt says what
                    capability = ""
            else:
                body = groups.get("body") or ""
                tail = groups.get("tail") or ""
                if index in (2, 3) and not _is_tool_phrase(body):
                    continue
                if index == 2 and not _says_none_exists(groups.get("there"), body, tail):
                    continue
                capability = _capability(body, tail)
            return MissingTool(sentence=sentence, capability=capability)
    return None


def admits_missing_tool(text: Optional[str]) -> bool:
    return find_missing_tool(text) is not None


def names_own_tool(sentence: str, own_tools: Collection[str]) -> bool:
    """True when the sentence names one of the agent's own tools (then nothing is really missing)."""
    return any(name and name in (sentence or "") for name in own_tools)
