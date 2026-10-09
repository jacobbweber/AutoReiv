# AutoReiv user guide

This guide walks through AutoReiv from a user's point of view. To install it first, see [Install and uninstall](install-and-uninstall.md).

## The studios

The left sidebar opens each studio. On a phone the same studios open full screen.

| Studio | What you do there |
|---|---|
| **Chat Studio** | Talk to an agent. Pick the agent at the top, open **Sessions** for earlier chats and **Options** for a new chat. |
| **Wiki** | Your notes: plain markdown files in the data folder, with folders, a mind map and an inbox for new notes. |
| **Projects** | Pick a code project folder for the Architect and Developer agents to work on. |
| **Agents** | Agent Studio: each agent's instructions, tone, model and skills (switch skills on or off). |
| **Skill Studio** | Read and edit skills (the step-by-step runbooks agents follow). |
| **Tools Studio** | See every tool, and turn on or off the tools that agents have built. |
| **Routines** | Scheduled jobs: see when they run, run one now, pause it, and read its history. |
| **Metrics** | How agents are doing: turns, tokens, speed, errors and logs. |
| **Settings** | Model providers, models, the data folder, backups, software updates and colour themes. |
| **Prompts** | Save prompts you use often and reuse them in Chat. |
| **Study** | Opens the Tutor in study mode with your current topic or course. |
| **Education** | Courses from your notes, plus quiz, flashcard and test players and your progress. |

## The agents

AutoReiv ships with these agents. Each one has its own instructions and skills, and you can change both in **Agents**.

| Agent | What it is for |
|---|---|
| **AutoReiv** | Your main companion: everyday questions, wiki notes and keeping the platform healthy. Start here. |
| **Tutor** | Teaches from your own wiki notes: courses, questions, quizzes and flashcards. |
| **Architect** | Plans changes to a code project with you, writes the work as cards and hands them to Developer. |
| **Developer** | Takes a card from Architect and plans, builds and checks the change in the active project. |
| **Toolsmith** | Builds a small new tool when you press **Ask Developer** (see below). |
| **Direct** | Talks straight to the model with no tools, handy for comparing models or a quick chat. |

Editing a shipped agent saves your own copy in the data folder; **Use shipped version** goes back to the original. Hiding a shipped agent can be undone with **Unhide**.

## Skills and tools

- A **tool** is one thing an agent can do, such as reading a wiki note or running a command.
- A **skill** is a short runbook that tells an agent how to do a kind of task, and which tools it needs.
- An agent can use the tools of the skills that are switched on for it in **Agents**.

If an agent says it has no tool for something, the reply ends with **Ask Developer**. Press it and Toolsmith writes the tool, checks it, and saves it switched off. You turn it on in **Tools Studio** when you are happy with it.

## Approvals and Auto-run

Reading is always allowed. Before an agent writes files, runs a shell command or runs code, the chat shows an approval card and waits for **Approve** or **Reject**.

Turn on **Auto-run** in Chat to let those tools run without asking in that chat. Tools that are blocked stay blocked either way.

## Jobs

For bigger tasks, tick **Run as a job** before sending. AutoReiv first plans the work (it can only read while planning), then runs it step by step and checks the result. The job's progress shows above the chat, and a stopped job can be continued from where it stopped. The box unticks itself after sending, so ordinary messages stay ordinary chats.

## Routines

AutoReiv comes with a few built-in routines that run at night, in your computer's local time:

| Routine | When |
|---|---|
| Nightly SRE Health Pulse (checks AutoReiv's own health) | every night at 2:00 AM |
| Education Retrieval + Retention (your due reviews) | every night at 2:30 AM |
| Wiki Inbox Curation | every night at 3:00 AM |
| Weekly Note Rollover & Task Carry-Over | Mondays at 4:00 AM |
| Autonomous Telemetry Auditor (looks for friction in recent chats) | every night at 4:30 AM |

Routines never run just because AutoReiv started. If the computer was off at the scheduled time, that run is skipped and the routine waits for its next time. You can run any routine by hand from **Routines**, or create your own.

## Models

Add providers in **Settings**:

- **Local:** Ollama, vLLM and LM Studio, on this computer or another one on your network.
- **Frontier:** OpenAI, Anthropic, Google Gemini, OpenRouter, Groq, DeepSeek and Together AI (you need an API key).

Settings also lists the models each provider offers, and the **Hardware Fit** section estimates which local models fit your computer's memory. Pick a default model in Settings, and give an agent its own model in **Agents** if you want.

## Updates, backups and your data

- **Updates:** **Settings > System & Software Updates** shows your version and branch. **Check for Updates** looks for new commits and **Update now** applies them. AutoReiv only moves forward (it never resets your copy) and first copies your database into the data folder's `backups` folder. On Docker the same panel shows the command to upgrade the container instead.
- **Backups:** in Settings, press **Create Backup Now** or choose a schedule (hourly, daily or weekly) and how many backups to keep. From a terminal, `autoreiv backup` makes one and `autoreiv restore <backup.zip> --yes` restores one.
- **Your data** stays in one data folder (see the table in the [README](../README.md#where-your-data-lives-and-how-it-is-kept-safe)). Uninstalling, updating and rolling back never delete it.

## Command line

The `autoreiv` command is installed with AutoReiv:

| Command | What it does |
|---|---|
| `autoreiv serve` | Starts AutoReiv (options: `--host`, `--port`, `--reload`). |
| `autoreiv status` | Shows the computer, database and agent status. |
| `autoreiv chat [agent]` | Chats with an agent in the terminal (default: AutoReiv). |
| `autoreiv routine list` | Lists routines. `autoreiv routine run <id>` runs one now. |
| `autoreiv backup` | Zips the data folder into its `backups` folder. |
| `autoreiv restore <zip> --yes` | Replaces the data folder from a backup zip. |
