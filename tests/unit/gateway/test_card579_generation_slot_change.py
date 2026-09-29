"""CARD-579: changing max concurrent generations while a reply runs or waits must not hang it."""

from __future__ import annotations

import asyncio

import pytest

from src.application.gateway.generation_semaphore import GenerationSemaphore

pytestmark = pytest.mark.asyncio


async def _hold(sem: GenerationSemaphore, started: asyncio.Event, release: asyncio.Event, log: list, name: str):
    async with sem:
        log.append(f"{name}+")
        started.set()
        await release.wait()
        log.append(f"{name}-")


async def test_a_waiter_still_runs_after_the_cap_changes_and_changes_back():
    """The live bug: 1 -> 2 while a reply waited left it on the replaced semaphore forever."""
    sem = GenerationSemaphore(1)
    log: list = []
    a_started, a_release = asyncio.Event(), asyncio.Event()
    b_started, b_release = asyncio.Event(), asyncio.Event()
    a = asyncio.create_task(_hold(sem, a_started, a_release, log, "a"))
    await a_started.wait()
    b = asyncio.create_task(_hold(sem, b_started, b_release, log, "b"))
    await asyncio.sleep(0.01)
    assert sem.waiting == 1
    sem.set_max_concurrent(3)
    sem.set_max_concurrent(1)
    await asyncio.sleep(0.01)
    a_release.set()
    await asyncio.wait_for(b_started.wait(), 1.0)
    b_release.set()
    await asyncio.wait_for(asyncio.gather(a, b), 1.0)
    assert sem.in_use == 0 and sem.waiting == 0


async def test_raising_the_cap_starts_a_queued_generation_now():
    sem = GenerationSemaphore(1)
    log: list = []
    a_started, a_release = asyncio.Event(), asyncio.Event()
    b_started, b_release = asyncio.Event(), asyncio.Event()
    a = asyncio.create_task(_hold(sem, a_started, a_release, log, "a"))
    await a_started.wait()
    b = asyncio.create_task(_hold(sem, b_started, b_release, log, "b"))
    await asyncio.sleep(0.01)
    assert not b_started.is_set()
    sem.set_max_concurrent(2)
    await asyncio.wait_for(b_started.wait(), 1.0)  # a still holds its slot
    assert sem.in_use == 2
    a_release.set()
    b_release.set()
    await asyncio.gather(a, b)
    assert sem.in_use == 0


async def test_lowering_the_cap_applies_as_running_generations_finish():
    sem = GenerationSemaphore(2)
    log: list = []
    ev = {n: (asyncio.Event(), asyncio.Event()) for n in "abc"}
    a = asyncio.create_task(_hold(sem, *ev["a"], log, "a"))
    b = asyncio.create_task(_hold(sem, *ev["b"], log, "b"))
    await ev["a"][0].wait()
    await ev["b"][0].wait()
    sem.set_max_concurrent(1)
    c = asyncio.create_task(_hold(sem, *ev["c"], log, "c"))
    await asyncio.sleep(0.01)
    ev["a"][1].set()
    await asyncio.sleep(0.01)
    assert not ev["c"][0].is_set()  # one still running, cap is 1
    ev["b"][1].set()
    await asyncio.wait_for(ev["c"][0].wait(), 1.0)
    ev["c"][1].set()
    await asyncio.gather(a, b, c)
    assert sem.in_use == 0


async def test_a_cancelled_waiter_does_not_leak_a_slot():
    sem = GenerationSemaphore(1)
    log: list = []
    a_started, a_release = asyncio.Event(), asyncio.Event()
    a = asyncio.create_task(_hold(sem, a_started, a_release, log, "a"))
    await a_started.wait()
    b = asyncio.create_task(_hold(sem, asyncio.Event(), asyncio.Event(), log, "b"))
    await asyncio.sleep(0.01)
    b.cancel()
    with pytest.raises(asyncio.CancelledError):
        await b
    a_release.set()
    await a
    assert sem.in_use == 0
    async with sem:
        assert sem.in_use == 1
    assert sem.in_use == 0


async def test_a_cap_change_from_a_worker_thread_wakes_the_loop():
    """Sync settings routes run in a thread pool; the wake-up must reach the event loop."""
    sem = GenerationSemaphore(1)
    log: list = []
    a_started, a_release = asyncio.Event(), asyncio.Event()
    b_started, b_release = asyncio.Event(), asyncio.Event()
    a = asyncio.create_task(_hold(sem, a_started, a_release, log, "a"))
    await a_started.wait()
    b = asyncio.create_task(_hold(sem, b_started, b_release, log, "b"))
    await asyncio.sleep(0.01)
    await asyncio.to_thread(sem.set_max_concurrent, 2)
    await asyncio.wait_for(b_started.wait(), 1.0)
    a_release.set()
    b_release.set()
    await asyncio.gather(a, b)
    assert sem.in_use == 0
