"""PreToolUse hook: block unsafe writes and unsafe shell commands (exit code 2)."""
import json
import os
import sys

SECRET_MARKERS = ["sk-ant-", "AKIA", "BEGIN PRIVATE KEY"]
LOCKED_PREFIXES = [".claude/hooks/", ".github/"]
LOCKED_FILES = [".claude/settings.json", "specs/constitution.md"]


# Stop the tool call: print the reason on stderr and exit with code 2.
def block(reason: str) -> None:
    print("policy_guard blocked this action: " + reason, file=sys.stderr)
    sys.exit(2)


# Return the project folder (CLAUDE_PROJECT_DIR, or cwd as a fallback).
def project_dir(data: dict) -> str:
    folder = os.environ.get("CLAUDE_PROJECT_DIR") or data.get("cwd") or os.getcwd()
    return os.path.realpath(folder)


# Return the file path a tool wants to write (empty string if none).
def get_target_path(tool_input: dict) -> str:
    if "file_path" in tool_input:
        return str(tool_input["file_path"])
    if "notebook_path" in tool_input:
        return str(tool_input["notebook_path"])
    return ""


# Return all the new text a tool wants to write, joined together.
def get_new_text(tool_input: dict) -> str:
    parts = []
    for key in ["content", "new_string", "new_source"]:
        if key in tool_input:
            parts.append(str(tool_input[key]))
    for edit in tool_input.get("edits", []):
        parts.append(str(edit.get("new_string", "")))
    return "\n".join(parts)


# Return the path relative to the project, with forward slashes, or None if outside.
def relative_to_project(path: str, root: str) -> str | None:
    full = path
    if not os.path.isabs(full):
        full = os.path.join(root, full)
    full = os.path.normcase(os.path.realpath(full))
    base = os.path.normcase(root)
    if full != base and not full.startswith(base + os.sep):
        return None
    return os.path.relpath(full, base).replace(os.sep, "/")


# Check the path rules for a file write.
def check_path(path: str, root: str) -> None:
    rel = relative_to_project(path, root)
    if rel is None:
        block("path is outside the project: " + path)
    if os.path.basename(rel).lower().startswith(".env"):
        block("writing .env files is not allowed: " + rel)
    for locked in LOCKED_FILES:
        if rel.lower() == locked.lower():
            block("this file is locked: " + rel)
    for prefix in LOCKED_PREFIXES:
        if (rel.lower() + "/").startswith(prefix.lower()):
            block("this folder is locked: " + rel)


# Check the new text for secret-like strings.
def check_secrets(text: str) -> None:
    for marker in SECRET_MARKERS:
        if marker in text:
            block("new text contains a secret-like string (" + marker + ")")


# Check a shell command: no git push, no .env (but .env.example is fine).
def check_command(command: str) -> None:
    if "git push" in command:
        block("git push is not allowed; the human pushes")
    cleaned = command.replace(".env.example", "")
    if ".env" in cleaned:
        block("commands that touch .env are not allowed")


# Read the hook JSON from stdin and apply the rules for the tool.
def main() -> None:
    data = json.loads(sys.stdin.read())
    tool_name = data.get("tool_name", "")
    tool_input = data.get("tool_input", {})
    if tool_name == "Bash":
        check_command(str(tool_input.get("command", "")))
        sys.exit(0)
    path = get_target_path(tool_input)
    if path != "":
        check_path(path, project_dir(data))
    check_secrets(get_new_text(tool_input))
    sys.exit(0)


if __name__ == "__main__":
    main()
