"""AutoReiv's own concepts, in a few lines every agent is sent [CARD-680].

A fresh wiki has no notes about AutoReiv itself, so without this an agent asked "what is a standing Job?"
searched the wiki and logs a dozen times and then guessed. Keep it short, plain and true to the product.
"""

from __future__ import annotations

AUTOREIV_CONCEPTS = """## About AutoReiv (answer questions about AutoReiv itself from this, without tools)
- Chat: talk to an agent. A tool that needs approval shows an approval card first.
- Standing Job: a goal AutoReiv works on in phases until its done-when holds. It starts only when you tick "Run as a job" in Chat (or a Routine has Run as a job on). Phases run in order: an optional Research phase, Formulate (plan the work), then Execute (do it). Each phase has a success rule; a job can wait for your approval and ends done, failed or cancelled.
- Routine: a saved prompt that runs on a schedule (cron or interval) in the Routines studio, with pause, run now and history. It runs as a standing Job only when its Run as a job setting is on.
- Agent: a profile (prompt, tone, model, allowed tools and skills) edited in Agent Forge. Shipped agents: AutoReiv, Developer, Tutor, Architect, Direct.
- Skill: a runbook (SKILL.md) an agent can open for step-by-step instructions; skills are turned on or off per agent.
- Wiki: your local Markdown notes in the data folder; agents search, read and write them.
- Education: courses, lessons and quizzes with the Tutor; due reviews come back on a 1-3-7-30 day schedule.
- Capability gap: when no tool can do what you asked, AutoReiv says so, records the gap and offers to ask the Developer to build the tool.
- Your data (database, wiki, agents, skills) lives in the data folder; updates, rollbacks and uninstall never delete it."""
