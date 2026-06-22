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
| TakeOff MCP | `paracore-pro` | `mcp_core/tools.py` (validate, handle_result) |

## Development

Clone alongside `paracore` and `paracore-pro`:

```
Paracore/
├── paracore-agent/    ← this repo
├── paracore/           ← desktop app + free addin
└── paracore-pro/       ← specialized MCPs + commercial addin
```

Each consumer adds this repo to `sys.path` at import time. No submodules, no pip install needed.
