"""Audit hook: append one JSON line per event to logs/audit.jsonl. Never blocks."""
import json
import os
import sys
from datetime import datetime, timezone


# Return the project folder (CLAUDE_PROJECT_DIR, or cwd as a fallback).
def project_dir(data: dict) -> str:
    return os.environ.get("CLAUDE_PROJECT_DIR") or data.get("cwd") or os.getcwd()


# Return a short description of what the event acted on (never file contents).
def get_target(data: dict) -> str:
    event = data.get("hook_event_name", "")
    tool_input = data.get("tool_input", {}) or {}
    if event == "UserPromptSubmit":
        return str(data.get("prompt", ""))[:200]
    if "file_path" in tool_input:
        return str(tool_input["file_path"])
    if "notebook_path" in tool_input:
        return str(tool_input["notebook_path"])
    if "command" in tool_input:
        return str(tool_input["command"])[:200]
    if "subagent_type" in tool_input:
        return str(tool_input["subagent_type"])
    return ""


# Build the log record for one event.
def build_record(data: dict) -> dict:
    return {
        "ts": datetime.now(timezone.utc).isoformat(),
        "session_id": data.get("session_id", ""),
        "event": data.get("hook_event_name", ""),
        "tool_name": data.get("tool_name", ""),
        "target": get_target(data),
    }


# Append the record as one line to logs/audit.jsonl.
def write_record(record: dict, root: str) -> None:
    log_dir = os.path.join(root, "logs")
    os.makedirs(log_dir, exist_ok=True)
    path = os.path.join(log_dir, "audit.jsonl")
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(record) + "\n")


# Read the hook JSON from stdin and log it. Any error is ignored.
def main() -> None:
    try:
        data = json.loads(sys.stdin.read())
        write_record(build_record(data), project_dir(data))
    except Exception:
        pass
    sys.exit(0)


if __name__ == "__main__":
    main()
