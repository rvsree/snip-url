"""Stop hook: run tests when src/ or tests/ changed. Block twice, then roll back."""
import json
import os
import subprocess
import sys
from datetime import datetime, timezone

MAX_RETRIES = 2
NO_TESTS_EXIT_CODE = 5


# Return the project folder (CLAUDE_PROJECT_DIR, or cwd as a fallback).
def project_dir() -> str:
    return os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()


# Return the current UTC time as an ISO string.
def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# Append one event line to logs/audit.jsonl.
def log_event(root: str, event: str, session_id: str, target: str) -> None:
    record = {"ts": now_iso(), "session_id": session_id, "event": event,
              "tool_name": "", "target": target}
    os.makedirs(os.path.join(root, "logs"), exist_ok=True)
    with open(os.path.join(root, "logs", "audit.jsonl"), "a", encoding="utf-8") as handle:
        handle.write(json.dumps(record) + "\n")


# Return True if git reports changes under src/ or tests/.
def has_code_changes(root: str) -> bool:
    result = subprocess.run(["git", "status", "--porcelain", "--", "src", "tests"],
                            cwd=root, capture_output=True, text=True)
    return result.stdout.strip() != ""


# Read the failure counter from logs/verify_state.json.
def read_counter(root: str) -> int:
    try:
        with open(os.path.join(root, "logs", "verify_state.json"), encoding="utf-8") as handle:
            return int(json.load(handle).get("counter", 0))
    except Exception:
        return 0


# Save the failure counter to logs/verify_state.json.
def write_counter(root: str, counter: int) -> None:
    os.makedirs(os.path.join(root, "logs"), exist_ok=True)
    with open(os.path.join(root, "logs", "verify_state.json"), "w", encoding="utf-8") as handle:
        json.dump({"counter": counter}, handle)


# Run pytest with coverage and return (exit code, output text).
def run_tests(root: str) -> tuple[int, str]:
    result = subprocess.run(
        ["uv", "run", "pytest", "--cov=snip_url", "--cov-fail-under=80", "-q"],
        cwd=root, capture_output=True, text=True)
    return result.returncode, result.stdout + result.stderr


# Return the last 30 lines of the text.
def last_lines(text: str) -> str:
    lines = text.splitlines()
    return "\n".join(lines[-30:])


# Stash src/ and tests/ (including untracked files) as a rollback.
def roll_back(root: str) -> None:
    message = "snip-url rollback " + now_iso()
    subprocess.run(["git", "stash", "push", "--include-untracked", "-m", message,
                    "--", "src", "tests"], cwd=root, capture_output=True, text=True)


# Handle a failed test run: block for a retry, or roll back after too many.
def handle_failure(root: str, session_id: str, output: str) -> None:
    counter = read_counter(root) + 1
    if counter <= MAX_RETRIES:
        write_counter(root, counter)
        log_event(root, "verify_fail", session_id, "attempt " + str(counter))
        reason = ("Tests failed (attempt " + str(counter) + " of " + str(MAX_RETRIES)
                  + "): " + last_lines(output))
        print(json.dumps({"decision": "block", "reason": reason}))
        return
    roll_back(root)
    write_counter(root, 0)
    log_event(root, "rollback", session_id, "src tests")
    message = ("Rolled back after 2 failed retries. "
               "Recover with git stash list / git stash pop.")
    print(json.dumps({"systemMessage": message}))


# Run the gate: skip if no code changes, otherwise test and decide.
def main() -> None:
    try:
        data = json.loads(sys.stdin.read())
    except Exception:
        data = {}
    session_id = data.get("session_id", "")
    root = project_dir()
    if not has_code_changes(root):
        sys.exit(0)
    code, output = run_tests(root)
    if code == 0 or code == NO_TESTS_EXIT_CODE:
        write_counter(root, 0)
        log_event(root, "verify_pass", session_id, "pytest exit " + str(code))
        sys.exit(0)
    handle_failure(root, session_id, output)
    sys.exit(0)


if __name__ == "__main__":
    main()
