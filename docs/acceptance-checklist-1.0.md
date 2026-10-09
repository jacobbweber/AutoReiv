# AutoReiv 1.0 acceptance checklist

Run this once on a **clean, throwaway data folder** before calling a build 1.0. Never run it against your day-to-day data folder.
Write the date, the commit, the machine and the model on the card (CARD-661), with pass or fail for every step.

## Setup

1. Pick an empty folder that does not exist yet, for example `%LOCALAPPDATA%\AutoReiv-1.0-checklist` on Windows or `~/autoreiv-1.0-checklist` on Linux.
2. Start AutoReiv with that folder as its data folder and a free port, for example:
   `AUTOREIV_DATA_DIR=<folder> python -m src.cli.main serve --port 8790`
3. Use one model that is already loaded. Do not load or swap models for this run.

## Steps

| # | Step | Pass when |
|---|------|-----------|
| 1 | **Fresh install.** Start on the empty data folder. | `/api/health` answers 200, and the data folder now has `database/`, `wiki/`, `agents/` and `skills/`. |
| 2 | **Real chat.** Open a new chat and ask a short question. | The answer streams back and the chat shows up in the session list with its messages. |
| 3 | **Wiki action.** Create a note in the Wiki (for example `00_Inbox/checklist-note.md`) and open it again. | The note opens with the text you wrote, and the file is in the data folder's `wiki/`. |
| 4 | **Course step.** Start a course on any topic and complete one step. | The course moves to the next step, and the completed step is recorded. |
| 5 | **Skill toggle.** In Agent Studio, turn one skill off for an agent (or on, if it was off). | The agent's skill list shows the change after a page reload. |
| 6 | **Routine.** Create a routine (or pick an existing one) and run it once. | The run is recorded in the routine's history with a finished status. |
| 7 | **Restart.** Stop AutoReiv and start it again with the same data folder. | `/api/health` answers 200 again. |
| 8 | **Persistence.** After the restart, look for the chat, the note, the course progress, the skill change and the routine run. | All five are still there, unchanged. |

## After the run

- Record the results on CARD-661.
- Stop the AutoReiv you started for this run.
- Keep the throwaway data folder until the results are recorded. Delete it only if Jacob agrees.
