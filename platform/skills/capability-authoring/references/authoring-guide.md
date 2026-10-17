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

## 2. `tools/<tool_name>.py`
- The tool name is the filename stem (`<tool_name>`).
- Must define a top-level `def run(...)` function with type annotations on every parameter (`str`, `int`, `float`, `bool`, `list`, `dict`).
- AutoReiv's AST loader infers the JSON Schema from `def run(...)` and the tool description from the module/function docstring—no manual JSON schema stub is needed.
- Set `RISK = "read_only"` for pure computation/lookup helpers, or `RISK = "write"` for mutating tools.

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
