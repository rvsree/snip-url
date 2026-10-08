# 01 - Project setup (build step 1)

**Date:** 2026-10-07
**Purpose:** Create the empty project: config, constitution, CLAUDE.md, permissions, CI, folder skeleton.

## Prompt

```
Read docs/project_brief.md. It is the approved brief for this project. Keep that file name; do not rename or move it.

Task: Build step 1 only (section 11, step 1). Do not start step 2 or later.

Create only these:
1. git repo: run git init.
2. .gitignore: Python defaults, .venv/, .env, .env.*, but NOT .env.example; data/*.db; logs/*.jsonl; .coverage; .pytest_cache/; __pycache__/; .idea/; .vscode/
3. .env.example: one line, ANTHROPIC_API_KEY= (no value).
4. pyproject.toml: project name snip-url, package snip_url, src layout, Python >=3.12, build backend hatchling.
   Dependencies: fastapi, uvicorn, pydantic. Dev group: pytest, pytest-cov, httpx.
   Add [tool.pytest.ini_options] with testpaths = ["tests"] and pythonpath = ["src"].
5. src/snip_url/__init__.py with one docstring line only. No other source files or subfolders.
6. Empty folders, each with a .gitkeep file: data/, logs/, scripts/, tests/,
   specs/001-core-api/, specs/002-alias-ratelimit-fix/, specs/003-viral-traffic/
7. CLAUDE.md (under 60 lines): what the project is; files to read first (docs/project_brief.md, specs/constitution.md, the current feature folder); all feature work goes through /sdlc with 3 human approvals; the "Never" rules (never read or print .env, never push, never git add -A or git add ., never weaken or delete a test to pass); commands for Windows PowerShell (uv sync, uv run pytest --cov=snip_url, uv run uvicorn snip_url.main:app --reload).
8. specs/constitution.md: coding standards:
   - Beginner-readable Python: explicit for loops and if/else, no list comprehensions, no lambdas
   - Type hints on all functions; one-line comment above every function
   - Functions under 30 lines
   - Layers: api/ has no business logic, services/ has no SQL, repo/ has SQL only, models/ has Pydantic models, common/ has config and errors
   - Errors returned as JSON: {"error": {"code": "...", "message": "..."}}
   - Tests named test_AC<n>_<what>, temporary SQLite via tmp_path, never the real database
   - Minimum 80% test coverage
   - Build only what the approved spec asks for
9. .claude/settings.json: permissions only, no hooks yet.
   Deny: reading .env and .env.* ; git push ; git add -A ; git add .
   Use the correct Claude Code permission rule syntax.
10. .github/workflows/ci.yml: on push and pull_request; ubuntu-latest; install uv; Python 3.12; uv sync; then run pytest with coverage. pytest exits with code 5 when no tests exist yet, so treat exit code 5 as success, and any other non-zero code as failure.
11. README.md stub: title, 2-line summary, setup commands for Windows PowerShell, an empty "Limitations" heading.

Rules:
- First show me your plan: every file you will create, one line each. Then STOP and wait for my "yes". Write nothing before that.
- Never read or print .env.
- Do not run git add, git commit or git push. I will do that.
- Do not create anything not listed above (no agents, skills, hooks, app code, tests or other docs).
- After writing, run: uv sync   and show me only the last 5 lines of output.
```

## Reply to the plan

```
yes. One change: use "git init -b main" so the branch is named main. Keep your other choices as proposed.
```

## Result

- 18 files created; `uv sync` passed; CI green on GitHub.
- Commit `40c59be` "Step 1: project setup (config, constitution, CLAUDE.md, CI)".
- Done by hand afterwards (not by Claude Code): added `requirements.txt` (`uv export`), changed `.env.example` to `DATABASE_PATH=data/snip_url.db`. Commit [INSERT commit ID].
