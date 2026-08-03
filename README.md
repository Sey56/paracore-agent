# Paracore MCP

The generalist Model Context Protocol server for Paracore — enables Claude Desktop,
Cursor, VS Code, and any MCP-compatible client to explore and control Revit through
natural language.

## What it does

Connects to the Paracore Addin running in Revit (via gRPC on `localhost:50051`)
and provides MCP tools for running C# code dynamically:

- **`ping`** — verify connection to Revit
- **`explore_revit_data`** — run read-only C# for discovery (never modifies the model)
- **`execute_dynamic_query`** — run read-write C# with auto-transaction wrapping
- **`search_schema`** — fast parameter schema lookup per Revit category
- **`read_extension_methods`** — the full Paracore extension methods catalog

## Build

```powershell
./build-mcp.ps1
```

Requirements: Python 3.12, Inno Setup 6.

Produces: `installers/Paracore-MCP-v4.7.0.exe`

## Install

1. Install the **Paracore Addin** from the [`paracore`](https://github.com/datadrivenconstruction/paracore) repo
2. Run `installers/Paracore-MCP-v4.7.0.exe`
3. Configure Claude Desktop to use the MCP server

## Structure

```
mcp_core/           Shared foundation — tools, validation, summarizer, gRPC client
  skills/           9 operation-based skill resources (query-filter, write-modify, etc.)
  prompts/          Composable system prompt
mcp_server.py       MCP server — stdio entry point
grpc_client.py      gRPC communication with the Paracore Addin
```

## Skills

Nine operation-based skills replace the monolithic extension methods catalog. Each
skill is a focused `SKILL.md` resource. Claude Desktop discovers them automatically.

| Skill | Covers |
|-------|--------|
| query-filter | GetElements, WhereParam, WhereMatches, OrderByParam |
| aggregate-group | GroupByParam, SumParam |
| parameter-access | GetStr, GetNum, GetInt, GetVal, NativeProperties |
| write-modify | SetVal, SetNum, SetParam, Delete, Transact |
| display-visualize | Table, Select projection, Println |
| discovery-debug | CombinedParams, NativeProperties, ParamsDict |
| create-geometry | Wall.Create, Floor.Create, FamilyInstance placement |
| identity-orientation | FamilyName, Matches, GetElementType |
| materials-units | Materials, MaterialNames, InputUnit, OutputUnit |

## License

MIT
