# snip-url

A small URL shortener (FastAPI + SQLite). The app is the example product.
What is graded is the controlled agentic workflow around it: a requirement
goes in, and a reviewed, tested result comes out, with humans approving the
high-impact steps.

## Read first

1. `docs/project_brief.md` - the approved brief (do not rename or move it)
2. `specs/constitution.md` - coding standards and layer rules
3. The current feature folder, e.g. `specs/001-core-api/`

## Workflow

All feature work goes through `/sdlc specs/<feature>`. It has 3 human approvals:

1. Approval 1 - the spec
2. Approval 2 - the plan (and tasks)
3. Approval 3 - the merge (the human commits; the human pushes)

Build only what the approved spec asks for. Do not skip or reorder steps.

## Never

- Never read or print `.env` or any `.env.*` file.
- Never push to a remote (`git push`).
- Never run `git add -A` or `git add .`; add named files only.
- Never weaken, skip or delete a test to make it pass. Fix the code instead.

## Layout

- `src/snip_url/` - app code (api/, services/, repo/, models/, common/)
- `tests/` - pytest tests
- `specs/` - constitution and one folder per feature
- `logs/` - `audit.jsonl` is tracked as evidence; only `logs/*.log` and `logs/verify_state.json` are git-ignored
- `scripts/` - helper scripts

## Commands (Windows PowerShell)

```powershell
uv sync
uv run pytest --cov=snip_url
uv run uvicorn snip_url.main:app --reload
```
