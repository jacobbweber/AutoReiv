# AutoReiv

Hi, I'm Jacob 👋 AutoReiv is my first real attempt at building an AI app, and I built it to learn. It is a multi-agent control plane: one place to run a small team of AI agents on your own machine, using local models (vLLM, Ollama, LM Studio) or plugging in frontier models from the big providers.

Two projects inspired me a lot along the way: [Hermes Agent](https://github.com/NousResearch/hermes-agent) and [OpenClaw](https://github.com/openclaw/openclaw). I never set out to copy their code. I wanted to learn from their concepts and ideas, try them my own way, and see where I could improve on them. AutoReiv is the result, and it is still a learning project, so expect it to keep changing.

---

## What AutoReiv does

AutoReiv runs on your computer (or a small server on your home network) and opens in your browser. From there you can:

- **Chat with agents** that use tools, read and write your notes, and ask before doing anything risky.
- **Keep a wiki** of plain markdown notes that agents can search, summarize and tidy up.
- **Study** with a Tutor that turns your own notes into courses, quizzes and flashcards.
- **Run routines** that do small jobs on a schedule, such as a nightly health check or tidying the wiki inbox.
- **Choose your models** per agent: a local model for everyday work, a frontier model when you want more power.

Everything you create (chats, notes, settings, agents and skills) is stored in one data folder on your machine.

## Quick start

AutoReiv needs Python 3.10, 3.11 or 3.12 (3.12 recommended) and Git. Pick one way to run it. Full steps, options and uninstall instructions are in **[Install and uninstall](docs/install-and-uninstall.md)**.

**Try it from a terminal (Windows, Linux or macOS):**

```bash
git clone https://github.com/jacobbweber/AutoReiv.git
cd AutoReiv
python -m venv .venv
# Windows: .\.venv\Scripts\Activate.ps1    Linux or macOS: source .venv/bin/activate
pip install -e .
autoreiv serve
```

Then open **http://127.0.0.1:8000** in your browser.

**Run it as a background service:**

- Windows service: `.\deploy\windows\install_windows_service.ps1` from an Administrator PowerShell (needs [NSSM](https://nssm.cc/)).
- Linux systemd: `sudo ./deploy/systemd/install_systemd.sh`
- Docker: `docker compose up -d`

Each of these starts AutoReiv on port 8000. See [Install and uninstall](docs/install-and-uninstall.md) for the options (port, service name, data folder).

## Your first steps

1. **Connect a model.** Open **Settings** and add a provider: a local one (Ollama, vLLM or LM Studio) or a frontier one (OpenAI, Anthropic, Google Gemini, OpenRouter, Groq, DeepSeek or Together AI). Pick a default model.
2. **Say hello.** Open **Chat Studio**, pick the **AutoReiv** agent and ask a question. Replies stream in, and the chat is saved.
3. **Write a note.** Open **Wiki**, create a note, then ask AutoReiv in Chat to summarize it or file it.
4. **Study something.** Press **Study** to learn from your notes with the Tutor, or open **Education** for quizzes and flashcards.
5. **Look at your routines.** Open **Routines** to see the built-in night-time routines and run one by hand.

The [User guide](docs/user-guide.md) walks through every studio, the agents and how approvals work.

## Where your data lives, and how it is kept safe

All your data lives in one data folder, separate from the code:

| How you run AutoReiv | Data folder |
|---|---|
| Windows (terminal or service) | `%LOCALAPPDATA%\AutoReiv`, for example `C:\Users\<you>\AppData\Local\AutoReiv` |
| Linux or macOS from a terminal | `~/.autoreiv` |
| Linux systemd service | `/var/lib/autoreiv` |
| Docker | the `autoreiv-data` volume (mounted at `/data`) |

You can choose another folder with `AUTOREIV_DATA_DIR` or the installer's data folder option.

- **Uninstalling never deletes your data.** Reinstall with the same data folder and everything is back.
- **Updates and rollbacks keep your data.** Before an update from **Settings > System & Software Updates**, AutoReiv copies the database into the `backups` folder.
- **Backups.** In **Settings**, press **Create Backup Now** or set a backup schedule (hourly, daily or weekly). From a terminal: `autoreiv backup`, and `autoreiv restore <backup.zip> --yes` to restore.
- **Risky actions need your OK.** Agents ask before running write, shell or code tools unless you turn on **Auto-run** for that chat.

## Learn more

- [User guide](docs/user-guide.md): studios, agents, skills and tools, jobs, routines, models, updates.
- [Install and uninstall](docs/install-and-uninstall.md): every install path, data folders, update and rollback.
- [Deployment scripts](deploy/README.md): every option of the install and uninstall scripts.
- [Developer guide](docs/developer.md): code layout, tests and how changes are made.
- [All docs](docs/README.md) and the [changelog](CHANGELOG.md).

The repository lives at https://github.com/jacobbweber/AutoReiv. The teaching path that led here is in [script-to-agent-labs](https://github.com/jacobbweber/script-to-agent-labs).
