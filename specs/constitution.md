# Constitution: coding standards

These rules apply to every feature. Agents and humans follow them.

## Code style

- Beginner-readable Python: explicit `for` loops and `if/else`.
- No list comprehensions. No lambdas.
- Type hints on all functions.
- A one-line comment above every function.
- Functions are under 30 lines.

## Layers

| Folder | Allowed | Not allowed |
|---|---|---|
| `api/` | Routes: parse request, call a service, return response | Business logic |
| `services/` | Business rules | SQL |
| `repo/` | SQL only | Business rules |
| `models/` | Pydantic models | Logic, SQL |
| `common/` | Config and errors | Business logic |

Calls go one way: api -> services -> repo.

## Errors

Errors are returned as JSON:

```json
{"error": {"code": "...", "message": "..."}}
```

## Tests

- Test names follow `test_AC<n>_<what>` (AC = acceptance criterion in the spec).
- Use a temporary SQLite database via `tmp_path`. Never the real database.
- Minimum 80% test coverage.
- Never weaken, skip or delete a test to make it pass.

## Scope

- Build only what the approved spec asks for.
