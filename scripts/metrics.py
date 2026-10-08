"""Read logs/audit.jsonl, print a metrics table, and write docs/metrics.md."""
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent.parent
LOG_PATH = ROOT / "logs" / "audit.jsonl"
OUT_PATH = ROOT / "docs" / "metrics.md"
HOOK_EVENTS = ["verify_fail", "verify_pass", "rollback"]
NO_STARTS = ["no ", "no,", "no:"]
MAX_GAP_SECONDS = 30 * 60

# Read the JSONL file into a list of events, skipping bad lines.
def read_events(path: Path) -> list:
    events = []
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            try:
                event = json.loads(line)
                event["time"] = datetime.fromisoformat(event["ts"])
            except (ValueError, KeyError):
                continue
            events.append(event)
    return events

# Return True when the event is a "/sdlc " prompt from the user.
def is_sdlc_prompt(event: dict) -> bool:
    is_prompt = event.get("event") == "UserPromptSubmit"
    return is_prompt and event.get("target", "").startswith("/sdlc ")

# Group events by session id, keeping the order of first appearance.
def group_by_session(events: list) -> dict:
    sessions = {}
    for event in events:
        sessions.setdefault(event.get("session_id", ""), []).append(event)
    return sessions

# Read (subject, commit time) from git history (empty list if git fails).
def read_commits() -> list:
    cmd = ["git", "log", "--format=%s|%cI"]
    try:
        out = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True,
                             check=True).stdout
    except (OSError, subprocess.CalledProcessError):
        return []
    commits = []
    for line in out.splitlines():
        subject, _, stamp = line.rpartition("|")
        try:
            commits.append((subject, datetime.fromisoformat(stamp)))
        except ValueError:
            continue
    return commits

# Return the earliest commit time whose subject starts with "<name>:", or None.
def find_commit_time(name: str, commits: list) -> Optional[datetime]:
    found = None
    for subject, when in commits:
        if subject.startswith(name + ":") and (found is None or when < found):
            found = when
    return found

# Split one session into runs: a hook test before /sdlc, then one per /sdlc.
def split_session(session: list) -> list:
    runs = []
    before = []
    hooked = False
    current = None
    for event in session:
        if is_sdlc_prompt(event):
            name = event["target"][len("/sdlc "):].strip()
            current = {"name": name, "start": event["time"], "events": []}
            runs.append(current)
        if current is None:
            before.append(event)
            hooked = hooked or event.get("event") in HOOK_EVENTS
        else:
            current["events"].append(event)
    if hooked:
        runs.append({"name": "hook test", "start": before[0]["time"],
                     "events": before})
    return runs

# Split every session into runs.
def split_into_runs(events: list) -> list:
    runs = []
    for session in group_by_session(events).values():
        runs.extend(split_session(session))
    return runs

# Return the start time of a run (used as the sort key).
def run_start(run: dict) -> datetime:
    return run["start"]

# Return True when a reply starts with "no" in one of the accepted forms.
def is_no_reply(text: str) -> bool:
    text = text.strip().lower()
    for start in NO_STARTS:
        if text.startswith(start):
            return True
    return text == "no"

# Count prompts, replies, retries, rollbacks and agent calls in a run.
def count_run(events: list) -> dict:
    counts = {"prompts": 0, "no": 0, "fail": 0, "rollback": 0, "agents": {},
              "menus": 0, "stop": False}
    for event in events:
        kind = event.get("event")
        target = event.get("target", "")
        if kind == "UserPromptSubmit":
            counts["prompts"] += 1
            if counts["prompts"] > 1 and is_no_reply(target):
                counts["no"] += 1
            if "stop here" in target.lower():
                counts["stop"] = True
        elif kind == "verify_fail":
            counts["fail"] += 1
        elif kind == "rollback":
            counts["rollback"] += 1
        elif kind == "PostToolUse" and event.get("tool_name") == "Agent":
            counts["agents"][target] = counts["agents"].get(target, 0) + 1
        elif kind == "PostToolUse" and event.get("tool_name") == "AskUserQuestion":
            counts["menus"] += 1
    return counts

# Keep events up to the commit time, or up to the first gap over 30 minutes.
def trim_events(events: list, commit_time: Optional[datetime]) -> list:
    kept = []
    for event in events:
        past_commit = commit_time is not None and event["time"] > commit_time
        gap = 0.0
        if commit_time is None and kept:
            gap = (event["time"] - kept[-1]["time"]).total_seconds()
        if past_commit or gap > MAX_GAP_SECONDS:
            break
        kept.append(event)
    return kept

# Turn one run into a row of metrics.
def summarize_run(run: dict, commits: list) -> dict:
    commit_time = find_commit_time(run["name"], commits)
    events = trim_events(run["events"], commit_time)
    counts = count_run(events)
    end = events[-1]["time"] if commit_time is None else commit_time
    seconds = max((end - events[0]["time"]).total_seconds(), 0.0)
    outcome = "incomplete"
    if commit_time is not None:
        outcome = "committed"
    elif counts["stop"]:
        outcome = "stopped at spec"
    return {"name": run["name"], "start": run["start"],
            "hook": run["name"] == "hook test",
            "minutes": seconds / 60, "outcome": outcome,
            "replies": max(counts["prompts"] - 1, 0), "no": counts["no"],
            "fail": counts["fail"], "rollback": counts["rollback"],
            "agents": counts["agents"], "menus": counts["menus"]}

# List (fail time, pass time, seconds) for each verify_fail and the next pass.
def find_mttr_pairs(events: list) -> list:
    pending = {}
    pairs = []
    for event in events:
        key = event.get("session_id", "")
        if event.get("event") == "verify_fail":
            pending.setdefault(key, []).append(event["time"])
        elif event.get("event") == "verify_pass":
            for failed_at in pending.get(key, []):
                seconds = (event["time"] - failed_at).total_seconds()
                pairs.append((failed_at, event["time"], seconds))
            pending[key] = []
    return pairs

# Compute totals; hook tests count in retries/rollbacks but not in success rate.
def build_totals(rows: list, pairs: list) -> dict:
    scored = good = retries = rollbacks = 0
    for row in rows:
        retries += row["fail"]
        rollbacks += row["rollback"]
        if row["hook"]:
            continue
        scored += 1
        if row["outcome"] in ("committed", "stopped at spec"):
            good += 1
    rate = "n/a"
    if scored > 0:
        rate = "%.0f%%" % (100.0 * good / scored)
    total = 0.0
    for pair in pairs:
        total += pair[2]
    mttr = "%.1f" % (total / len(pairs)) if pairs else "n/a"
    return {"runs": len(rows), "scored": scored, "rate": rate,
            "retries": retries, "rollbacks": rollbacks, "mttr": mttr}

# Format agent call counts as "name=count, name=count".
def format_agents(counts: dict) -> str:
    parts = []
    for name, number in counts.items():
        parts.append("%s=%d" % (name, number))
    return ", ".join(parts) or "-"

# Format a time in UTC, with seconds when asked.
def format_time(when: datetime, seconds: bool) -> str:
    pattern = "%Y-%m-%d %H:%M:%S" if seconds else "%Y-%m-%d %H:%M"
    return when.astimezone(timezone.utc).strftime(pattern)

# Build the report lines (table plus totals) as Markdown.
def render_report(rows: list, totals: dict, pairs: list) -> list:
    lines = ["| Scenario | Start (UTC) | Minutes | Outcome | Replies | No replies "
             "| Menu decisions | Retries | Rollbacks | Agent calls |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    for row in rows:
        start = format_time(row["start"], False)
        lines.append("| %s | %s | %.1f | %s | %d | %d | %d | %d | %d | %s |" % (
            row["name"], start, row["minutes"], row["outcome"], row["replies"],
            row["no"], row["menus"], row["fail"], row["rollback"], format_agents(row["agents"])))
    lines.append("")
    lines.append("- Runs: %d (%d scored, %d hook test)" % (
        totals["runs"], totals["scored"], totals["runs"] - totals["scored"]))
    lines.append("- Success rate (committed or stopped at spec, hook tests "
                 "excluded): %s" % totals["rate"])
    lines.append("- Total retries: %d" % totals["retries"])
    lines.append("- Total rollbacks: %d" % totals["rollbacks"])
    lines.append("- MTTR (seconds): %s" % totals["mttr"])
    lines.append("- MTTR pairs (fail time, pass time, seconds):")
    for pair in pairs:
        lines.append("  - %s, %s, %.1f" % (format_time(pair[0], True),
                                          format_time(pair[1], True), pair[2]))
    return lines

# Read the log, print the report, and write docs/metrics.md.
def main() -> None:
    events = read_events(LOG_PATH)
    runs = sorted(split_into_runs(events), key=run_start)
    commits = read_commits()
    rows = []
    for run in runs:
        rows.append(summarize_run(run, commits))
    pairs = find_mttr_pairs(events)
    lines = render_report(rows, build_totals(rows, pairs), pairs)
    print("\n".join(lines))
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    header = ["# Reliability metrics", "", "Generated " + stamp + ".", ""]
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text("\n".join(header + lines) + "\n", encoding="utf-8")

if __name__ == "__main__":
    main()
