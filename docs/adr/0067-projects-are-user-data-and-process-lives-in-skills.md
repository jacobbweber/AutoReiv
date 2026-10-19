# ADR-0067: Projects are user data and process lives in skills

> **Date**: 2026-10-18  
> **Status**: Accepted  
> **Deciders**: Jacob Weber, AutoReiv Agent  
> **Guard Test**: `tests/unit/architecture/test_card728_projects_user_data.py`  
> **Amends**: [ADR-0066](./0066-consolidate-architect-developer-and-toolsmith-into-agora-skill-folders-on-autoreiv.md) (Projects Studio template scaffold and drift/align are retired; `software-development` may run commands through `cli_exec`)

---

## 1. Context & Problem Statement
Projects Studio asked the operator for a free `projects_root` path and browsed whatever filesystem the serve saw. In
Docker that is the container image, so host folders could not be picked, and any folder (including the running
AutoReiv checkout `/app`) could be selected. At the same time AutoReiv's own engineering process was built into the
studio and its tools: `create_project` copied the `templates/sdlc-project` scaffold, and `detect_drift` /
`align_project` flagged every repo that did not match it and offered to write it in. A repo cloned from GitHub that
already has its own `AGENTS.md`, `CLAUDE.md`, Copilot or Cursor rules was treated as "drifted".

Jacob wants AutoReiv to set up projects (clone, pull, push), develop full applications and games with devops know-how,
and follow spec-driven development where a repo uses it, without imposing AutoReiv's process on other repos.

---

## 2. Decision Drivers
* Same behaviour on native installs and Docker (no host-filesystem traversal from a container).
* Respect a repo's own conventions; offer AutoReiv's starter files only when a repo has none.
* Keep the safety rules mechanical (path jail, protected branches, approvals); move workflow know-how to skills.
* One code path per job (ADR-0061, code-quality rules).

---

## 3. Considered Options
* **Option 1 (Chosen)**: Projects live in one user-data folder (`<data>/projects/`, env `AUTOREIV_PROJECTS_DIR`
  overrides at deploy time, Docker mounts it like the wiki). Process (onboarding a repo, spec-driven development,
  cards) lives in platform skills; tools keep only safety rules.
* **Option 2**: Keep a free `projects_root` setting and add a host-side MCP "project runner" so Docker can reach host
  folders and toolchains.
* **Option 3**: Keep the free setting, document that Projects only works on native installs.

---

## 4. Decision Outcome
Chosen option: **Option 1**, because it works the same everywhere, needs no second process, and removes the template
pressure on other repos. Option 2 stays possible later if a host toolchain (Unity, Unreal) is needed.

Rules this ADR sets (each enforced by the guard test):
1. **One projects folder.** `DataDirResolver().resolve().projects_path` is `AUTOREIV_PROJECTS_DIR` when set, else
   `<data root>/projects`. There is no `projects_root` setting and no `/api/settings/projects_root` endpoint.
2. **Selection stays inside it.** A selected project must be a folder inside the projects folder and never the running
   AutoReiv checkout. A stored selection outside it is ignored (no old-format reader).
3. **No template push.** No `detect_drift` / `align_project` tools or endpoints, no `templates/sdlc-project` copy.
   `create_project` makes an empty folder with `git init`. Starter files (`AGENTS.md`, cards, specs) are written by
   the agent following a skill, only when the repo has none or the operator asks.
4. **Process lives in skills.** `repo-onboarding` (discover and adopt a repo's conventions),
   `spec-driven-development` (spec, plan, tasks), `project-cards` (opt-in cards) and `software-development` (edit,
   run, check, commit). `software-development` may run project commands with `cli_exec` (approval per call, the
   dangerous-command filter still blocks).

### Positive Consequences
* Docker and native behave the same; the operator can open the same folder in VS Code on the host.
* Cloned repos keep their own rules; AutoReiv adapts to them.

### Negative Consequences / Trade-offs
* Existing selections outside the projects folder are dropped; the operator re-selects (or clones) once.
* Commands run where the serve runs: a Docker serve only has the toolchains in its image.

---

## 5. Pros and Cons of Options

### Option 1
* Good, because one rule for every install, mirrors the wiki mount.
* Bad, because projects elsewhere on the host must be moved, cloned, or the folder pointed at them with
  `AUTOREIV_PROJECTS_DIR`.

### Option 2
* Good, because full host toolchains and credentials.
* Bad, because a second process, a network path into a host shell, and the project tools would move out of the serve.

### Option 3
* Good, because no work.
* Bad, because Docker users get a studio that cannot work.
