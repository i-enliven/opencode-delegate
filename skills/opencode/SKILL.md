---
name: opencode
description: "Delegate coding to OpenCode via the opencode-delegate plugin (features, PR review, session management)."
version: 1.4.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [Coding-Agent, OpenCode, Autonomous, Refactoring, Code-Review]
    related_skills: [claude-code, codex, hermes-agent]
---

# OpenCode via opencode-delegate plugin

Use the opencode-delegate plugin tools to hand bounded coding tasks to [OpenCode](https://opencode.ai), an autonomous coding agent, and to manage OpenCode sessions. The plugin wraps `opencode run` as a subprocess and returns structured JSON results — no terminal/process tools needed.

## Tools Provided

| Tool | Purpose |
|------|---------|
| `opencode_delegate` | Delegate a bounded coding task to OpenCode |
| `opencode_session_list` | List OpenCode sessions (find IDs to resume) |
| `opencode_session_show` | Inspect a session's details and recent transcript |
| `opencode_session_delete` | Delete a session by ID (permanent) |

## When to Use

- User explicitly asks to use OpenCode
- You want an external coding agent to implement/refactor/review code
- You want parallel task execution in isolated workdirs
- You need a bounded, one-shot delegation with a structured result
- You need to find, inspect, resume, or clean up OpenCode sessions

## Prerequisites

- The opencode-delegate plugin installed and registered (provides the four tools above)
- OpenCode CLI installed — the plugin auto-detects it on `PATH`, in `~/.nvm/versions/node/*/bin/opencode`, or `~/.opencode/bin/opencode`
- Auth configured: `opencode auth login` or provider env vars (OPENROUTER_API_KEY, etc.)
- Git repository for code tasks (recommended)

## Basic One-Shot Task

```
opencode_delegate(goal="Add retry logic to API calls and update tests", workdir="~/project")
```

`workdir` defaults to the current session cwd; a missing directory is pre-created automatically.

## Attaching Context Files

Use `files` to hand OpenCode specific files as context:

```
opencode_delegate(goal="Review this config for security issues", files=["config.yaml", ".env.example"])
```

## Forcing a Model or Agent

```
opencode_delegate(goal="Refactor auth module", model="openrouter/anthropic/claude-sonnet-4")
opencode_delegate(goal="Draft a migration plan", agent="plan")
```

## Structured Output (session, tokens, cost)

Pass `format="json"` to get machine-readable results including the OpenCode session ID and token usage:

```
opencode_delegate(goal="Fix issue #101", format="json")
# → {"ok": true, "exit_code": 0, "session_id": "ses_abc123", "tokens": {...}, "cost": 0}
```

## Continuing a Session

Feed the `session_id` from a JSON-format run back in as `session` to continue that conversation in a follow-up call:

```
opencode_delegate(goal="Now add error handling for token expiry", session="ses_abc123")
```

Or continue the most recent session with `continue=true`. `session` takes precedence over `continue`.

Note: a resumed run with `format="json"` returns only structured fields (session_id, tokens, cost) — use plain-text format (omit `format`) when you need the reply text itself.

## Session Management

Find sessions to resume:

```
opencode_session_list(limit=20)
opencode_session_list(workdir="~/project")  # only sessions in that directory
# → {"ok": true, "sessions": [{"id": "ses_abc123", "title": "...", "updated": ..., "created": ..., "directory": "..."}]}
```

Inspect a session before resuming it (recent transcript, role/text per message):

```
opencode_session_show(session="ses_abc123", last_messages=10)
# → {"ok": true, "session": {...}, "messages": [{"role": "user", "text": "...", "created": ...}, ...]}
```

Delete a session (permanent, cannot be undone):

```
opencode_session_delete(session="ses_abc123")
```

Typical loop: delegate with `format="json"` → get `session_id` → later, `opencode_session_list`/`opencode_session_show` to find and verify it → `opencode_delegate(session=...)` to resume.

## Parameter Reference

| Parameter  | Type     | Description |
|------------|----------|-------------|
| `goal`     | string   | Required. The coding task for OpenCode |
| `workdir`  | string   | Working directory (default: session cwd); created if missing |
| `timeout`  | integer  | Seconds to allow; default 600, clamped 30–1800 |
| `model`    | string   | Force a specific model via `--model` |
| `agent`    | string   | Agent name via `--agent` (e.g. `build`, `plan`) |
| `files`    | string[] | File paths attached via `--file` |
| `session`  | string   | Session ID to continue via `--session` |
| `continue` | boolean  | Continue the last session via `--continue` |
| `format`   | string   | `json` for structured output (session_id, tokens, cost) |

## Response Format

Default (plain text): `{"ok": bool, "exit_code": int|null, "output": str, "error": str|null}`

With `format="json"`: `{"ok": bool, "exit_code": int|null, "session_id": str|null, "tokens": obj|null, "cost": num|null, "stderr": str|null, "error": str|null}`

Output is truncated to the last 8000 characters. All failures return `ok: false` with a descriptive `error` — the tool never raises.

## PR Review Workflow

Review a PR in a temporary clone for isolation:

```
opencode_delegate(
  goal="Review this PR vs main. Report bugs, security risks, test gaps, and style issues.",
  workdir="/tmp/pr-review-42",
  files=[".gitignore", "README.md"]
)
```

Clone the repo into the workdir first (e.g. via a terminal command), then delegate the review against it.

## Parallel Work Pattern

Use separate workdirs to avoid collisions; run multiple delegations and collect results:

```
opencode_delegate(goal="Fix issue #101 and commit", workdir="/tmp/issue-101")
opencode_delegate(goal="Add parser regression tests and commit", workdir="/tmp/issue-102")
```

## Session & Cost Management

- Token usage and cost per run: use `format="json"` and read `tokens`/`cost` from the result
- Session listing, transcript inspection, deletion: use `opencode_session_list`, `opencode_session_show`, `opencode_session_delete`
- Aggregate usage stats: use the CLI directly (`opencode stats`) via a terminal command — the plugin does not expose this

## Pitfalls

- The plugin runs `opencode run` (one-shot, non-interactive). It does NOT support interactive TUI sessions — for iterative work, use `session` continuation instead.
- Binary resolution is automatic (PATH → nvm → `~/.opencode/bin`), but if behavior differs between environments, verify with `which -a opencode` and `opencode --version`.
- Avoid sharing one working directory across parallel OpenCode delegations.
- Long tasks: raise `timeout` (max 1800s) rather than retrying; on timeout the partial output is returned with `ok: false`.
- If OpenCode appears stuck, the result will eventually time out — inspect OpenCode logs directly via the CLI if needed.
- `opencode_session_delete` is permanent — verify the session ID with `opencode_session_list` or `opencode_session_show` before deleting.
- Session tools have a short 60s CLI timeout; they are metadata operations, not task runs.

## Verification

Smoke test:

```
opencode_delegate(goal="Respond with exactly: OPENCODE_SMOKE_OK")
```

Success criteria:
- Result `ok: true` and output includes `OPENCODE_SMOKE_OK`
- No provider/model errors in `error`
- For code tasks: expected files changed and tests pass

## Rules

1. Prefer the plugin tools over raw `opencode` terminal commands — they give structured results, timeout control, and automatic binary resolution.
2. Use `format="json"` when you need the session ID, token counts, or cost.
3. Always scope a delegation to a single repo/workdir; use separate workdirs for parallel tasks.
4. For long tasks, provide progress updates by re-delegating with `session` continuation.
5. Report concrete outcomes (files changed, tests, remaining risks) back to the user.
6. Use the CLI directly (terminal) only for things the plugin does not expose: interactive TUI, `opencode stats`, `opencode pr`.
7. Before resuming a session from a past run, confirm it with `opencode_session_show` to check the transcript matches expectations.
