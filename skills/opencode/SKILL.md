---
name: opencode
description: "Delegate coding to OpenCode via the opencode-delegate plugin (features, PR review)."
version: 1.3.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [Coding-Agent, OpenCode, Autonomous, Refactoring, Code-Review]
    related_skills: [claude-code, codex, hermes-agent]
---

# OpenCode via opencode-delegate plugin

Use the `opencode_delegate` tool (from the opencode-delegate plugin) to hand bounded coding tasks to [OpenCode](https://opencode.ai), an autonomous coding agent. The plugin wraps `opencode run` as a subprocess and returns a structured JSON result — no terminal/process tools needed.

## When to Use

- User explicitly asks to use OpenCode
- You want an external coding agent to implement/refactor/review code
- You want parallel task execution in isolated workdirs
- You need a bounded, one-shot delegation with a structured result

## Prerequisites

- The opencode-delegate plugin installed and registered (provides the `opencode_delegate` tool)
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
- List past sessions / aggregate stats: use the CLI directly (`opencode session list`, `opencode stats`) via a terminal command — the plugin does not expose these

## Pitfalls

- The plugin runs `opencode run` (one-shot, non-interactive). It does NOT support interactive TUI sessions — for iterative work, use `session` continuation instead.
- Binary resolution is automatic (PATH → nvm → `~/.opencode/bin`), but if behavior differs between environments, verify with `which -a opencode` and `opencode --version`.
- Avoid sharing one working directory across parallel OpenCode delegations.
- Long tasks: raise `timeout` (max 1800s) rather than retrying; on timeout the partial output is returned with `ok: false`.
- If OpenCode appears stuck, the result will eventually time out — inspect OpenCode logs directly via the CLI if needed.

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

1. Prefer `opencode_delegate` over raw `opencode run` terminal commands — it gives structured results, timeout control, and automatic binary resolution.
2. Use `format="json"` when you need the session ID, token counts, or cost.
3. Always scope a delegation to a single repo/workdir; use separate workdirs for parallel tasks.
4. For long tasks, provide progress updates by re-delegating with `session` continuation.
5. Report concrete outcomes (files changed, tests, remaining risks) back to the user.
6. Use the CLI directly (terminal) only for things the plugin does not expose: interactive TUI, `opencode session list`, `opencode stats`, `opencode pr`.
