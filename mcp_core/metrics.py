"""
Lightweight tool-call metrics — no external dependencies.
Logs structured JSON to the same log directory as the MCP server.
"""

import json
import os
import time
import logging
from collections import defaultdict

logger = logging.getLogger("paracore-metrics")

_METRICS_DIR: str | None = None
_metrics: dict[str, list[dict]] = defaultdict(list)


def init(log_dir: str):
    """Set the log directory for metrics output."""
    global _METRICS_DIR
    _METRICS_DIR = log_dir
    os.makedirs(log_dir, exist_ok=True)


def record_tool_call(
    tool_name: str,
    success: bool,
    duration_ms: float,
    anti_pattern_blocked: bool = False,
    workflow_warning: bool = False,
    bulk_write_detected: bool = False,
    suspicious_params: int = 0,
    param_blocked: bool = False,
):
    """Record a single tool call with outcome and guardrail triggers."""
    entry = {
        "tool": tool_name,
        "success": success,
        "duration_ms": round(duration_ms, 1),
        "anti_pattern_blocked": anti_pattern_blocked,
        "workflow_warning": workflow_warning,
        "bulk_write_detected": bulk_write_detected,
        "suspicious_params": suspicious_params,
        "param_blocked": param_blocked,
        "timestamp": time.time(),
    }
    _metrics[tool_name].append(entry)

    # Write to file every 10 calls
    total = sum(len(v) for v in _metrics.values())
    if total % 10 == 0 and _METRICS_DIR:
        _flush()


def summarize() -> dict:
    """Return a summary of all recorded metrics."""
    result = {"total_calls": 0, "tools": {}}
    for tool_name, entries in _metrics.items():
        total = len(entries)
        if total == 0:
            continue
        successful = sum(1 for e in entries if e["success"])
        blocked = sum(1 for e in entries if e["anti_pattern_blocked"])
        warnings = sum(1 for e in entries if e["workflow_warning"])
        bulk = sum(1 for e in entries if e["bulk_write_detected"])
        susp = sum(1 for e in entries if e["suspicious_params"] > 0)
        durations = [e["duration_ms"] for e in entries]

        result["tools"][tool_name] = {
            "calls": total,
            "success_rate": f"{successful / total * 100:.1f}%",
            "anti_pattern_blocks": blocked,
            "workflow_warnings": warnings,
            "bulk_write_detections": bulk,
            "suspicious_param_warnings": susp,
            "p50_ms": _percentile(durations, 50),
            "p95_ms": _percentile(durations, 95),
        }
        result["total_calls"] += total
    return result


def _flush():
    """Write metrics to JSON file."""
    if not _METRICS_DIR:
        return
    path = os.path.join(_METRICS_DIR, "paracore_mcp_metrics.json")
    try:
        with open(path, "w") as f:
            json.dump(summarize(), f, indent=2)
    except Exception:
        pass


def _percentile(data: list[float], p: float) -> float:
    if not data:
        return 0.0
    sorted_data = sorted(data)
    k = (len(sorted_data) - 1) * p / 100.0
    f = int(k)
    c = k - f
    if f + 1 < len(sorted_data):
        return round(sorted_data[f] * (1 - c) + sorted_data[f + 1] * c, 1)
    return round(sorted_data[f], 1)
