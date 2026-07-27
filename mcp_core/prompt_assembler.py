"""
Prompt Assembler — builds the MCP system prompt from composable markdown files.

Single source of truth. All prompt content lives in mcp_core/prompts/*.md.
The assembler reads these at import time and caches them in memory.
"""

import os

_PROMPTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "prompts")

# Canonical source for EXTENSION_METHODS.md / REPL_GUIDE.md:
# ../paracore/ (free repo, public). Relative from mcp_core/ in
# paracore-agent: ../../paracore/
_PARACORE_FREE = os.path.normpath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "..", "paracore"))

_cache: dict[str, str] = {}
_full_prompt_cache: str | None = None


def _read(filename: str) -> str:
    """Read a prompt file from the prompts directory, with caching."""
    if filename in _cache:
        return _cache[filename]
    path = os.path.join(_PROMPTS_DIR, filename)
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        _cache[filename] = content
        return content
    except FileNotFoundError:
        return f"[Prompt file not found: {filename}]"


# ── Prompt sections (composed in order) ───────────────────────────────────

_SECTIONS = [
    "identity.md",
    "globals.md",
    "script-rules.md",
    "retrieval.md",
    "linq-rules.md",
    "parameter-discovery.md",
    "catalog.md",
    "critical-rules.md",
    "verification.md",
    "common-patterns.md",
]


def build_prompt() -> str:
    """Build the full MCP system prompt from composable sections."""
    global _full_prompt_cache
    if _full_prompt_cache is not None:
        return _full_prompt_cache

    parts = [_read(f) for f in _SECTIONS]
    prompt = "\n\n".join(parts)
    _full_prompt_cache = prompt
    return prompt


def _read_shared(filename: str) -> str | None:
    """Read a file from the canonical paracore free repo, falling back
    through dev/prod paths."""
    paths = [
        os.path.join(_PARACORE_FREE, filename),                       # dev: ../../paracore/
        os.path.join(os.path.dirname(_PARACORE_FREE), "paracore-agent",
                     filename),                                        # bundled: paracore-agent/ root
    ]
    for p in paths:
        try:
            with open(p, "r", encoding="utf-8") as f:
                return f.read()
        except (FileNotFoundError, OSError):
            continue
    return None


def build_extension_reference() -> str:
    """Build the extension methods reference from the canonical shared doc.
    Falls back to the abbreviated catalog.md if the full doc isn't available."""
    content = _read_shared("EXTENSION_METHODS.md")
    if content:
        return content
    # Last resort: abbreviated catalog in prompts/
    return _read("catalog.md")


def get_section(name: str) -> str:
    """Get a single section by filename (e.g., 'parameter-discovery.md')."""
    return _read(name)


def reload():
    """Clear caches so files are re-read on next access (useful for hot-reload)."""
    global _full_prompt_cache
    _cache.clear()
    _full_prompt_cache = None
