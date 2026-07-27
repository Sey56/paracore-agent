# Paracore Agent

The AI brain for Paracore — powers both the in-app agent (Paracore UI) and the
generalist MCP server (Claude Desktop / Cursor / VS Code).

## Structure

```
mcp_core/           Shared foundation — prompts, tools, validation, gRPC client
agent/              In-app agent — PydanticAI agent + FastAPI router
mcp_server.py       Generalist MCP — stdio entry point for MCP clients
grpc_client.py      gRPC communication with Paracore.Server / Paracore.Addin
```

## Consumers

| Consumer | Repo | What it uses |
|---|---|---|
| In-app agent | `paracore` | `agent/agent_router.py` (via FastAPI) |
| Generalist MCP | (self) | `mcp_server.py` (built as .exe) |
| Specialized MCPs | domain-specific repos | `mcp_core/` — tools, validation, gRPC client |

## Development

Clone alongside `paracore`:

```
Paracore/
├── paracore-agent/    ← this repo
└── paracore/           ← desktop app + free addin
```

Specialized MCP repos also consume `mcp_core/` from this repo.

Each consumer adds this repo to `sys.path` at import time. No submodules, no pip install needed.

## Skills

Nine operation-based skills under `mcp_core/skills/` replace the monolithic extension methods catalog. Each skill is a directory with a `SKILL.md` registered as a plain `@mcp.resource` under `skill://` URIs. Claude Desktop discovers them automatically.

The agent reads `paracore://skills` (served from `SKILLS.md`) to learn what's available, then pulls individual `skill://{name}/SKILL.md` resources as needed.

### Skill list

| Skill | Covers |
|---|---|
| query-filter | GetElements, WhereParam, WhereMatches, OrderByParam, Count, Any |
| aggregate-group | GroupByParam, SumParam |
| parameter-access | GetStr, GetNum, GetVal, GetInt, type-level accessors, native properties |
| write-modify | SetVal, SetNum, SetParam, Delete, Hide, Unhide, Isolate, Transact |
| display-visualize | Table, BarGraph, PieGraph, LineGraph, Println, Select projection |
| discovery-debug | CombinedParams, Peek, BuiltInParams, InstanceParams, TypeParams, GeometrySummary |
| create-geometry | Wall.Create, Floor.Create, FamilyInstance placement, XYZ, CurveLoop, InputUnit |
| identity-orientation | FamilyName, Matches, GetElementType, door handing/hinge methods |
| materials-units | Materials, MaterialNames, InputUnit, OutputUnit, IsAlmostEqualTo |

### Design

Operation-based, not category-based — `.WhereParam()` works identically on walls, rooms, and ducts. Partitioning by Revit category would duplicate endlessly. Partitioning by operation creates reusable, composable skills.

The LLM always starts with `query-filter` and pulls others as the task demands. A modification task never loads `create-geometry`. An exploration task never loads `write-modify`.

`_read_extension_methods` still returns the full catalog as a fallback.

### Registration

Skills are plain `@mcp.resource` functions — no `SkillProvider` dependency:

```python
_SKILL_DESCRIPTIONS = {
    "query-filter": "Element retrieval, filtering, and sorting — ...",
    ...
}
_SKILL_CACHE = {}
for name in _SKILL_DESCRIPTIONS:
    _SKILL_CACHE[name] = _load_resource(_get_skill_path(name) + "/SKILL.md", None)

def _make_skill_resource(name, description):
    @mcp.resource(f"skill://{name}/SKILL.md", description=description)
    def _skill():
        return _SKILL_CACHE.get(name, f"Skill not found: {name}")
    return _skill

for name, desc in _SKILL_DESCRIPTIONS.items():
    _make_skill_resource(name, desc)
```

Skill files are pre-loaded at startup into `_SKILL_CACHE` and served from RAM. Bundled via `--add-data "mcp_core/skills;mcp_core/skills"` in PyInstaller.
