# Agora Skill Folder Authoring Guide

Every user skill lives in `$DATA_DIR/skills/<skill_id>/` with up to three parts:

```text
skills/<skill_id>/
  SKILL.md
  references/
    <topic>.md
  tools/
    <tool_name>.py
```

## 1. `SKILL.md`
- Starts with YAML frontmatter (`name`, `description`, optional `tools:`).
- Keep the main body concise (< 200 lines). Put deep domain tables, schemas, or examples in `references/<topic>.md` and instruct the model to load them on demand via `skill_view(skill_id="<skill_id>", reference="<topic>.md")`.
- Never invent `/slash-commands` in `SKILL.md`; skills are runbooks opened with `skill_view(skill_id="<skill_id>")`.
- When you author a skill folder with `write_skill_file`, do not also call `propose_skill` or `commit_skill` for that skill.

## 2. `tools/<tool_name>.py`
- The tool name is the filename stem (`<tool_name>`).
- Must define a top-level `def run(...)` function with explicit type annotations on every parameter (`str`, `int`, `float`, `bool`, `list`, `dict`). Never write untyped `def run(**kwargs)`.
- AutoReiv's AST loader infers the JSON Schema from `def run(...)` and the tool description from the module/function docstring—no manual JSON schema stub is needed.
- Set `RISK = "read_only"` for pure computation/lookup helpers, or `RISK = "write"` for mutating tools.

## 3. Sandbox Subprocess Environment Contract
- Every colocated Python tool runs in an **isolated subprocess** whose current working directory is an ephemeral `/tmp/autoreiv_sandbox_*` directory—never the wiki vault or repository root.
- Always resolve paths from environment variables instead of relative `Path(rel_path).resolve()`:
  - `os.environ["AUTOREIV_WIKI_PATH"]` — root of the Wiki vault (`00_Inbox`, `01_Notes`, `02_Resources`, `03_Archive`).
  - `os.environ["AUTOREIV_DATA_DIR"]` — root of the live AutoReiv data directory.
  - `os.environ["AUTOREIV_PROJECTS_DIR"]` — root of the user projects directory.
- Native Python tools **cannot** import other AutoReiv platform tools (`from functions import ...` does not exist) or MCP tools (`from mcp_* import ...` does not exist). To orchestrate existing `mcp_*` or platform tools, list them in `SKILL.md` `tools:` frontmatter and call them from the agent turn instead of wrapping them in Python.
- When a tool touches files, the network, or external programs, `write_skill_file` saves it as `disabled` and automatically emits an inline `enable_skill_tool` **Approve / Reject** card in Chat so the operator can enable and mount it with one click.

### Example (`tools/convert_units.py`)
```python
"""Convert between metric and imperial units."""

RISK = "read_only"


def run(value: float, from_unit: str = "kg", to_unit: str = "lb") -> dict:
    """Convert value from from_unit to to_unit."""
    factors = {("kg", "lb"): 2.20462, ("lb", "kg"): 1 / 2.20462}
    factor = factors.get((from_unit.lower(), to_unit.lower()))
    if factor is None:
        return {"error": f"Unsupported conversion: {from_unit} -> {to_unit}"}
    return {"result": round(float(value) * factor, 4), "unit": to_unit}
```
