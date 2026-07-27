"""
Shared tool implementations — single source of truth for ALL tool logic.

Both the MCP server (mcp/mcp_server.py) and the in-app agent (agent/v4_repl_agent.py)
use these implementations. Each consumer wraps them with its own transport-specific
adapters (MCP: FastMCP positional args, Agent: PydanticAI models + ThinkingSteps).

SECURITY: Checks are ALWAYS enforced. No silent fallback. If tool_helpers can't
import, the module fails LOUD at import time — not silently at runtime.
"""

import logging
import time
from grpc_client import execute_repl
from mcp_core.metrics import record_tool_call

# ── Security imports — MUST succeed ──────────────────────────────────────
from mcp_core.tool_helpers import (
    sanitize_csharp_code,
    check_paracore_compliance,
    check_dangerous_patterns,
    check_suspicious_param_names,
    summarize_execution_result,
    format_execution_error,
    search_extension_methods,
)

logger = logging.getLogger("paracore-agent")


# ── Session state — workflow enforcement ─────────────────────────────────
# Soft guardrails: _execute_dynamic_query warns if no discovery happened first.
# Doesn't block — the user may have legitimate reasons to skip discovery.
# Resets on server restart (module-level state).

class _SessionState:
    def __init__(self):
        self.ping_called = False
        self.discovery_calls = 0       # _explore_revit_data or _search_schema
        self.modification_calls = 0    # _execute_dynamic_query

    def record_ping(self):            self.ping_called = True
    def record_discovery(self):       self.discovery_calls += 1
    def record_modification(self):    self.modification_calls += 1

    def workflow_warning(self) -> str | None:
        """Return a warning if modification is attempted without prior discovery."""
        if self.modification_calls > 0 and self.discovery_calls == 0:
            return (
                "WORKFLOW WARNING: _execute_dynamic_query called without any "
                "prior discovery (_explore_revit_data or _search_schema). "
                "Verify you have the correct parameter names and element counts "
                "before modifying the model. A bad parameter name returns empty "
                "results — indistinguishable from 'no matches.'\n\n"
            )
        return None

_SESSION = _SessionState()


# ── Shared messages ───────────────────────────────────────────────────────

USER_REJECTED_MSG = (
    "Code execution denied for this Revit session. "
    "Open Revit and approve the one-time session dialog, or restart Revit to reset."
)

READ_ONLY_VIOLATION_MSG = (
    "Read-only violation: exploration code contains write operations "
    "(SetVal, Delete, Transact, etc.). Use execute_dynamic_query for writes.\n\n"
    "Error: %s"
)


# ── Core helpers ───────────────────────────────────────────────────────────

def validate_csharp(csharp_code: str) -> str | None:
    """
    Run ALL security and compliance checks on C# code.
    Returns None if clean, or a formatted error message if violations found.

    This is the SINGLE enforcement point for ALL security — both MCP and Agent
    call it. No silent fallback, no import hacks, no separate code paths.
    """
    code = sanitize_csharp_code(csharp_code)

    compliance = check_paracore_compliance(code)
    if compliance:
        logger.info(f"Anti-pattern blocked: {compliance[:200]}")
        return compliance

    danger = check_dangerous_patterns(code, agent_only=True)
    if danger:
        logger.info(f"Dangerous pattern blocked: {danger[:200]}")
        return danger

    return None


def handle_execution_result(result: dict) -> str:
    """Process a gRPC execution result dict into a user-facing string."""
    if result.get("user_rejected"):
        return USER_REJECTED_MSG
    if result.get("read_only_violation"):
        err = result.get("error_message", "Unknown violation")
        if isinstance(err, list):
            err = "; ".join(str(e) for e in err)
        return READ_ONLY_VIOLATION_MSG % err
    if result["is_success"]:
        return summarize_execution_result(result)
    return format_execution_error(result)


# ── Tool implementations ───────────────────────────────────────────────────

def explore_revit_data(
    csharp_code: str,
    justification: str,
    *,
    session_id: str = "mcp-session",
    source: str = "mcp_agent",
) -> str:
    """
    Execute a READ-ONLY C# snippet in Revit for schema/data discovery.

    Results are summarized: first 5 table rows, first 10 text lines, + totals.
    BEFORE WRITING ANY C#: read paracore://system-prompt for the method catalog.

    PARACORE-FIRST: Use extension methods (.GetStr, .GetNum, .WhereParam,
    .OrderByParam, .GroupByParam, .SumParam, .Table, etc.) instead of raw
    LINQ, FilteredElementCollector, LookupParameter, or foreach+Println.
    """
    t0 = time.perf_counter()
    error = validate_csharp(csharp_code)
    if error:
        record_tool_call("explore_revit_data", False, (time.perf_counter() - t0) * 1000,
                         anti_pattern_blocked=True)
        return error

    param_warning = check_suspicious_param_names(csharp_code)
    suspicious_count = 1 if param_warning else 0
    _SESSION.record_discovery()
    logger.info(f"Exploring Revit data: {justification}")
    try:
        result = execute_repl(csharp_code, session_id,
                              execution_mode="read_only", source=source)
        duration_ms = (time.perf_counter() - t0) * 1000
        record_tool_call("explore_revit_data", result.get("is_success", False),
                         duration_ms, suspicious_params=suspicious_count)
        return param_warning + handle_execution_result(result)
    except Exception as e:
        duration_ms = (time.perf_counter() - t0) * 1000
        record_tool_call("explore_revit_data", False, duration_ms)
        logger.error(f"Exploration exception: {e}")
        return f"Error executing exploration script: {str(e)}"


def execute_dynamic_query(
    csharp_code: str,
    justification: str,
    *,
    session_id: str = "mcp-session",
    source: str = "mcp_agent",
) -> str:
    """
    Execute C# in Revit (read or modify). The user's final action.
    Results are summarized. SELF-CORRECTION: retry up to 3 times on errors.

    BEFORE WRITING ANY C#: call the read_extension_methods tool (NOT inside C# —
    it's a separate MCP tool call) to look up method syntax. The catalog in your
    system prompt already covers the most common methods; use this tool when you
    need a specific method signature or an overload you don't recognize.

    WRITES: el.SetVal("Comments","Done"), el.SetNum("Offset",-150,"cm"),
    el.Delete(), el.Hide(), el.Unhide(), el.Isolate() — auto-transact.
    Collection batch writes (ONE transaction): .SetParam("Comments","Done"),
    .Delete(), .Hide(), .Unhide(), .Isolate().
    Manual foreach loops: ALWAYS wrap in Transact().

    DISPLAY: ALWAYS use .Table(). NEVER foreach+Println loops.
    """
    import re

    t0 = time.perf_counter()
    error = validate_csharp(csharp_code)
    if error:
        record_tool_call("execute_dynamic_query", False, (time.perf_counter() - t0) * 1000,
                         anti_pattern_blocked=True)
        return error

    param_warning = check_suspicious_param_names(csharp_code)
    suspicious_count = 1 if param_warning else 0
    _SESSION.record_modification()

    # ── Workflow guard: warn if no discovery happened first ──────────────
    workflow_warning = _SESSION.workflow_warning()

    # ── Bulk write detection ─────────────────────────────────────────────
    _BULK_PATTERNS = [
        (r'\.SetParam\s*\(',     '.SetParam() — bulk parameter write on ALL filtered elements'),
        (r'\.Delete\s*\(',       '.Delete() — bulk delete on ALL filtered elements'),
        (r'\.Hide\s*\(',         '.Hide() — bulk hide on ALL filtered elements'),
        (r'\.Isolate\s*\(',      '.Isolate() — bulk isolate on ALL filtered elements'),
    ]
    bulk_warnings = []
    for pattern, desc in _BULK_PATTERNS:
        if re.search(pattern, csharp_code):
            bulk_warnings.append(desc)
    bulk_msg = ""
    if bulk_warnings:
        bulk_msg = (
            "BULK OPERATION DETECTED:\n"
            + "\n".join(f"  • {w}" for w in bulk_warnings)
            + "\n\nVerify the filter scope BEFORE proceeding. "
            + "Use .Count() first to check how many elements will be affected.\n\n"
        )

    prefix = param_warning + (workflow_warning or "") + bulk_msg

    logger.info(f"Executing dynamic query: {justification}")
    try:
        result = execute_repl(csharp_code, session_id, source=source)
        duration_ms = (time.perf_counter() - t0) * 1000
        record_tool_call("execute_dynamic_query", result.get("is_success", False),
                         duration_ms, suspicious_params=suspicious_count,
                         workflow_warning=bool(workflow_warning),
                         bulk_write_detected=bool(bulk_warnings))
        return prefix + handle_execution_result(result)
    except Exception as e:
        duration_ms = (time.perf_counter() - t0) * 1000
        record_tool_call("execute_dynamic_query", False, duration_ms)
        logger.error(f"Execution exception: {e}")
        return prefix + f"Error executing task script: {str(e)}"


def search_schema(category_name: str) -> str:
    """
    Search the model schema for parameter definitions of a Revit category.
    Returns parameter names, storage types, and whether each is Type or Instance.
    PREFERRED discovery tool — faster than running .CombinedParams().Table().
    Results are cached in memory after first call per category.
    """
    logger.info(f"Searching schema for: {category_name}")
    _SESSION.record_discovery()
    try:
        from mcp_core.schema_cache import search_schema as do_search
        result = do_search(category_name)
        # Append usage example so the LLM knows how to use the discovered params
        usage = (
            f"\n\n// To query {category_name}, use the parameter names above:\n"
            f'GetElements("{category_name}").Select(e => new {{ '
            f"Id = e.Id.IntegerValue, "
            f'Level = e.GetStr("Level"), '
            f'Name = e.GetStr("Name") '
            f'}}).Table()\n'
            f'// Or group by a discovered parameter:\n'
            f'GetElements("{category_name}").GroupByParam("Level").Table()'
        )
        return result + usage
    except Exception as e:
        logger.error(f"Schema search failed: {e}")
        return (
            f"Schema search failed: {str(e)}. "
            "Try explore_revit_data with .CombinedParams().Table() instead."
        )


def read_extension_methods(query: str = "") -> str:
    """
    Returns the Paracore Extension Methods reference.
    If 'query' is provided, returns only the relevant section.
    Leave empty for the full reference (capped at 15,000 chars).
    """
    from mcp_core.prompt_assembler import build_extension_reference
    doc = build_extension_reference()
    if query and query.strip():
        return search_extension_methods(query.strip(), doc)
    return doc[:15000]


def ping() -> str:
    """Diagnostic tool to verify the server is alive and responding.
    Returns 'pong' + a quick-start cheat sheet that primes the LLM context."""
    return """pong

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PARACORE QUICK-START — Read before writing any code
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

GLOBALS — use EXACTLY these names (PascalCase):
  Doc          → active Revit Document
  ActiveView   → current View
  Selection    → List<Element> of selected elements
  Println(msg) → output a line of text

QUERY — use Paracore methods, NOT raw Revit API:
  GetElements("Walls")           → all elements of that category
  GetElements<Wall>()            → typed retrieval
  GetElements("Walls").Count()   → element count

  .WhereParam("Name", "value")   → filter by parameter
  .GroupByParam("Name")          → group and count → chain .Table()
  .Select(e => new { ... })      → project columns → always put Id first → .Table()
  .Table()                       → render as interactive data grid
  .First().CombinedParams().Table() → discover ALL parameters on an element

WRITE (execute_dynamic_query only — auto-transacted):
  e.SetVal("Comments", "Done")
  e.SetNum("Offset", -150, "mm")
  GetElements("Walls").SetParam("Comments", "Done")   ← bulk, one transaction
  Transact("name", () => { /* foreach with writes */ })

PROJECT INFO: Doc.ProjectInformation.Name, Doc.Title, Doc.PathName, Doc.IsWorkshared

FORBIDDEN — these raw Revit API patterns will be REJECTED:
  new FilteredElementCollector(Doc)...
  doc  /  ActiveDocument  /  activeDocument  (use Doc)
  doc.ProjectInformation  (use Doc.ProjectInformation)
  .OfCategory(BuiltInCategory.OST_...)
  foreach+Println loops for data display (use .Table())"""


def get_globals() -> str:
    """Return the complete globals + pre-imported namespaces reference.
    Single source of truth: reads from mcp_core/prompts/globals.md."""
    from mcp_core.prompt_assembler import get_section
    return get_section("globals.md")

