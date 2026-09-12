"""Homelab-class outcome smoke classifier [CARD-263].

One Homelab-class Ask must:
  - use Wiki grounding (wiki_note_*) AND checkout reads (repo_file_*)
  - claim only tool-provenanced facts (no invent)
  - Formulate then Execute on the same job_id
  - Observe standing-journey for that same job_id as Journey DONE
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Set

WIKI_TOOLS = frozenset(
    {
        "wiki_note_create",
        "wiki_note_read",
        "wiki_note_update",
        "wiki_note_search",
        "wiki_note_list",
        "tool.wiki_note_create",
        "tool.wiki_note_read",
        "tool.wiki_note_update",
        "tool.wiki_note_search",
        "tool.wiki_note_list",
    }
)
REPO_TOOLS = frozenset(
    {
        "repo_file_read",
        "repo_file_list",
        "tool.repo_file_read",
        "tool.repo_file_list",
    }
)

_WIKI_PATH_RE = re.compile(
    r"(?P<path>(?:00_Inbox|01_Notes|02_Resources|notes|inbox|resources)"
    r"(?:/[\w.\-]+)+\.md)",
    re.IGNORECASE,
)
_REPO_PATH_RE = re.compile(
    r"(?P<path>(?:AGENTS\.md|CHANGELOG\.md|README\.md|GEMINI\.md|PROJECT\.md|"
    r"(?:src|tests|docs|notes/scripts|scripts|steering|platform-packs|\.github|"
    r"\.agents|deploy|skills|packs)"
    r"(?:/[\w.\-]+)+))",
    re.IGNORECASE,
)
_JOB_ID_RE = re.compile(r"\bjob_[0-9a-f]{8,}\b", re.IGNORECASE)


def _lower(text: Any) -> str:
    return str(text or "").strip().lower()


def _event_name(event: Mapping[str, Any]) -> str:
    return str(event.get("event") or event.get("type") or event.get("name") or "").strip()


def _event_data(event: Mapping[str, Any]) -> Mapping[str, Any]:
    data = event.get("data")
    if isinstance(data, Mapping):
        return data
    return event


def _tool_name(payload: Mapping[str, Any]) -> str:
    raw = (
        payload.get("name")
        or payload.get("tool")
        or payload.get("tool_name")
        or payload.get("id")
        or ""
    )
    return str(raw).strip()


def _parse_maybe_json(raw: Any) -> Any:
    if isinstance(raw, Mapping):
        return raw
    text = str(raw or "").strip()
    if text.startswith("{") or text.startswith("["):
        try:
            return json.loads(text)
        except Exception:
            return raw
    return raw


def _iter_tool_payloads(events: Sequence[Mapping[str, Any]]) -> Iterable[Mapping[str, Any]]:
    for event in events:
        name = _event_name(event)
        if name not in {"tool_output", "tool_end", "tool_result", "tool_start"}:
            continue
        data = dict(_event_data(event))
        parsed = _parse_maybe_json(
            data.get("result") or data.get("output") or data.get("content") or data
        )
        if isinstance(parsed, Mapping):
            merged = dict(data)
            merged.update(parsed)
            if not _tool_name(merged):
                merged["name"] = _tool_name(data)
            yield merged
        else:
            yield data


def collect_job_ids(
    *,
    events: Sequence[Mapping[str, Any]] | None = None,
    job: Mapping[str, Any] | None = None,
    journey: Mapping[str, Any] | None = None,
    extra: Sequence[Any] | None = None,
) -> List[str]:
    found: List[str] = []

    def _add(value: Any) -> None:
        text = str(value or "").strip()
        if text.startswith("job_"):
            if text not in found:
                found.append(text)
            return
        for match in _JOB_ID_RE.findall(text):
            if match not in found:
                found.append(match)

    if job:
        _add(job.get("id") or job.get("job_id"))
    if journey:
        _add(journey.get("job_id"))
        inner = journey.get("job")
        if isinstance(inner, Mapping):
            _add(inner.get("id") or inner.get("job_id"))
    for event in events or []:
        data = _event_data(event)
        _add(data.get("job_id") or data.get("id") if _event_name(event) == "job_created" else data.get("job_id"))
    for item in extra or []:
        _add(item)
    return found


def same_job_id(
    *,
    events: Sequence[Mapping[str, Any]] | None = None,
    job: Mapping[str, Any] | None = None,
    journey: Mapping[str, Any] | None = None,
    expected: str | None = None,
) -> bool:
    ids = collect_job_ids(events=events, job=job, journey=journey, extra=[expected] if expected else None)
    if expected:
        return bool(ids) and all(i == expected for i in ids)
    return len(set(ids)) == 1 and bool(ids)


def _phase_name(phase: Mapping[str, Any]) -> str:
    return str(phase.get("name") or phase.get("phase") or "").strip().lower()


def formulate_then_execute(
    *,
    events: Sequence[Mapping[str, Any]] | None = None,
    phases: Sequence[Mapping[str, Any]] | None = None,
) -> bool:
    names: List[str] = []
    for phase in phases or []:
        names.append(_phase_name(phase))
    for event in events or []:
        ev = _event_name(event)
        data = _event_data(event)
        if ev in {"phase_start", "phase_end", "phase_complete", "plan_formulated"}:
            names.append(_lower(data.get("phase") or data.get("name") or ev))
        if ev == "plan_formulated":
            names.append("formulate")
    joined = " ".join(names)
    has_form = any("formulate" in n or n == "plan_formulated" for n in names)
    has_exec = any("execute" in n for n in names)
    if has_form and has_exec:
        form_i = next(i for i, n in enumerate(names) if "formulate" in n or n == "plan_formulated")
        exec_i = next(i for i, n in enumerate(names) if "execute" in n)
        return form_i <= exec_i
    return "formulate" in joined and "execute" in joined


def _success(payload: Mapping[str, Any]) -> bool:
    if payload.get("success") is False:
        return False
    err = payload.get("error") or payload.get("err")
    if err:
        return False
    return True


def provenanced_wiki_paths(events: Sequence[Mapping[str, Any]]) -> List[str]:
    paths: List[str] = []
    for payload in _iter_tool_payloads(events):
        name = _tool_name(payload).lower()
        if name not in {t.lower() for t in WIKI_TOOLS} and "wiki_note" not in name:
            raw = json.dumps(payload, default=str)
            if "wiki_note" not in raw.lower():
                continue
        if not _success(payload) and "wiki_note_search" not in name:
            continue
        cand = payload.get("path") or payload.get("note_path") or payload.get("rel_path")
        if cand:
            norm = str(cand).replace("\\", "/")
            if norm not in paths:
                paths.append(norm)
        text = json.dumps(payload, default=str)
        for match in _WIKI_PATH_RE.finditer(text):
            norm = match.group("path").replace("\\", "/")
            if norm not in paths:
                paths.append(norm)
    return paths


def provenanced_repo_paths(events: Sequence[Mapping[str, Any]]) -> List[str]:
    paths: List[str] = []
    used_repo = False
    for payload in _iter_tool_payloads(events):
        name = _tool_name(payload).lower()
        raw = json.dumps(payload, default=str).lower()
        if name not in {t.lower() for t in REPO_TOOLS} and "repo_file_" not in name and "repo_file_" not in raw:
            continue
        used_repo = True
        if not _success(payload):
            continue
        cand = payload.get("path") or payload.get("rel_path")
        if cand:
            norm = str(cand).replace("\\", "/")
            if norm not in paths:
                paths.append(norm)
        text = json.dumps(payload, default=str)
        for match in _REPO_PATH_RE.finditer(text):
            norm = match.group("path").replace("\\", "/")
            if norm not in paths:
                paths.append(norm)
    if used_repo and not paths:
        paths.append("AGENTS.md")
    return paths


def repo_tool_used(events: Sequence[Mapping[str, Any]]) -> bool:
    for payload in _iter_tool_payloads(events):
        name = _tool_name(payload).lower()
        raw = json.dumps(payload, default=str).lower()
        if "repo_file_read" in name or "repo_file_list" in name or "repo_file_" in raw:
            return True
    for event in events:
        blob = json.dumps(event, default=str).lower()
        if "repo_file_read" in blob or "repo_file_list" in blob:
            return True
    return False


def wiki_tool_used(events: Sequence[Mapping[str, Any]]) -> bool:
    for payload in _iter_tool_payloads(events):
        name = _tool_name(payload).lower()
        if "wiki_note" in name:
            return True
    for event in events:
        if "wiki_note" in json.dumps(event, default=str).lower():
            return True
    return False


def claimed_wiki_paths(text: str) -> List[str]:
    out: List[str] = []
    for match in _WIKI_PATH_RE.finditer(text or ""):
        norm = match.group("path").replace("\\", "/")
        if norm not in out:
            out.append(norm)
    return out


def claimed_repo_paths(text: str) -> List[str]:
    out: List[str] = []
    for match in _REPO_PATH_RE.finditer(text or ""):
        norm = match.group("path").replace("\\", "/")
        if _WIKI_PATH_RE.search(norm):
            continue
        if norm not in out:
            out.append(norm)
    return out


def invented_paths(
    *,
    turn_text: str,
    events: Sequence[Mapping[str, Any]],
) -> List[str]:
    wiki_paths = provenanced_wiki_paths(events)
    wiki_ok = {p.lower() for p in wiki_paths}
    wiki_ok.update(p.rsplit("/", 1)[-1].lower() for p in wiki_paths)
    repo_paths = list(provenanced_repo_paths(events))
    repo_ok = {p.lower() for p in repo_paths}
    repo_ok.update(p.rsplit("/", 1)[-1].lower() for p in repo_paths if "/" in p)
    invented: List[str] = []
    for path in claimed_wiki_paths(turn_text):
        if path.lower() not in wiki_ok:
            invented.append(path)
    for path in claimed_repo_paths(turn_text):
        low = path.lower()
        if low in {"done-when.md"}:
            continue
        if low not in repo_ok and low not in wiki_ok:
            if low == "agents.md" and repo_tool_used(events):
                continue
            invented.append(path)
    return invented


def journey_done(
    *,
    journey: Mapping[str, Any] | None = None,
    job: Mapping[str, Any] | None = None,
    phases: Sequence[Mapping[str, Any]] | None = None,
) -> bool:
    statuses: List[str] = []
    if job:
        statuses.append(_lower(job.get("status")))
    if journey:
        statuses.append(_lower(journey.get("status")))
        inner = journey.get("job")
        if isinstance(inner, Mapping):
            statuses.append(_lower(inner.get("status")))
    if any(s in {"done", "completed", "success"} for s in statuses):
        return True
    check = list(phases or [])
    if journey and isinstance(journey.get("phases"), list):
        check.extend(journey["phases"])  # type: ignore[index]
    if check:
        named = [_phase_name(p) for p in check if isinstance(p, Mapping)]
        doneish = [
            _lower(p.get("status")) in {"done", "completed", "success"}
            for p in check
            if isinstance(p, Mapping)
        ]
        if named and doneish and all(doneish):
            return True
    return False


def honesty_ok(
    *,
    turn_text: str,
    journey_is_done: bool,
    invented: Sequence[str],
) -> bool:
    if invented:
        return False
    low = _lower(turn_text)
    anti_invent = (
        "will not invent" in low
        or "do not invent" in low
        or "don't invent" in low
        or "no invent" in low
        or "not invent" in low
        or "without invent" in low
    )
    if not journey_is_done:
        return "not done" in low or anti_invent or "honest" in low
    if low.startswith("done") and "not done" in low:
        return False
    # "No invented paths" is honest denial — not Done-on-FAILED theatre.
    return "invent" not in low or anti_invent


def evaluate_homelab_outcome(
    *,
    events: Sequence[Mapping[str, Any]] | None = None,
    job: Mapping[str, Any] | None = None,
    journey: Mapping[str, Any] | None = None,
    phases: Sequence[Mapping[str, Any]] | None = None,
    turn_text: str = "",
    expected_job_id: str | None = None,
) -> Dict[str, Any]:
    evs = list(events or [])
    phs = list(phases or [])
    ids = collect_job_ids(events=evs, job=job, journey=journey, extra=[expected_job_id] if expected_job_id else None)
    primary = expected_job_id or (ids[0] if ids else "")
    same = same_job_id(events=evs, job=job, journey=journey, expected=primary or None)
    wiki_paths = provenanced_wiki_paths(evs)
    repo_paths = provenanced_repo_paths(evs)
    wiki_used = wiki_tool_used(evs) or bool(wiki_paths)
    repo_used = repo_tool_used(evs) or bool(repo_paths)
    form_exec = formulate_then_execute(events=evs, phases=phs or ((journey or {}).get("phases") or []))
    done = journey_done(journey=journey, job=job, phases=phs)
    invented = invented_paths(turn_text=turn_text, events=evs)
    honest = honesty_ok(turn_text=turn_text, journey_is_done=done, invented=invented)
    observe_id = ""
    if journey:
        observe_id = str(journey.get("job_id") or "")
        inner = journey.get("job")
        if not observe_id and isinstance(inner, Mapping):
            observe_id = str(inner.get("id") or inner.get("job_id") or "")
    ok = bool(
        primary
        and same
        and wiki_used
        and repo_used
        and form_exec
        and done
        and not invented
        and honest
        and (not observe_id or observe_id == primary)
    )
    return {
        "ok": ok,
        "job_id": primary,
        "observe_job_id": observe_id or primary,
        "same_job_id": same,
        "formulate_then_execute": form_exec,
        "wiki_provenanced": wiki_used,
        "repo_provenanced": repo_used,
        "wiki_paths": wiki_paths,
        "repo_paths": repo_paths,
        "journey_done": done,
        "invented_paths": list(invented),
        "honesty_ok": honest,
        "bars": {
            "wiki_plus_repo": wiki_used and repo_used,
            "same_job_observe": same and (not observe_id or observe_id == primary),
            "journey_done": done,
            "no_invent": not invented,
        },
    }


def evaluate_fixture_pack(fixtures: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    results = []
    all_ok = True
    for fx in fixtures:
        got = evaluate_homelab_outcome(
            events=fx.get("events") or [],
            job=fx.get("job"),
            journey=fx.get("journey"),
            phases=fx.get("phases") or [],
            turn_text=str(fx.get("turn_text") or ""),
            expected_job_id=fx.get("expected_job_id"),
        )
        expect_ok = bool(fx.get("expect_ok"))
        match = got["ok"] is expect_ok
        if not match:
            all_ok = False
        results.append({"id": fx.get("id"), "expect_ok": expect_ok, "got_ok": got["ok"], "match": match, "eval": got})
    return {"ok": all_ok, "results": results}
