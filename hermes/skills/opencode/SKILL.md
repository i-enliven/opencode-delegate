---
name: opencode
description: "Delegate coding tasks, bug fixes, refactoring, PR reviews, and multi-turn development sessions to the OpenCode autonomous agent via opencode_delegate and opencode_session_* tools."
version: 1.5.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [Coding-Agent, OpenCode, Autonomous, Refactoring, Code-Review]
    related_skills: [claude-code, codex, hermes-agent]
---

# OpenCode Autonomous Delegation

Delegate bounded coding tasks, code reviews, and multi-turn refactoring to [OpenCode](https://opencode.ai) via plugin tools. The plugin manages subprocess execution, session persistence, automatic directory alignment, and structured JSON telemetry without requiring terminal interactions.

## Tool Index

| Tool | Purpose | Primary Arguments |
|------|---------|-------------------|
| `opencode_delegate` | Execute or continue a coding task | `goal`, `workdir`, `files`, `session`, `format`, `timeout`, `model` |
| `opencode_session_list` | Find past sessions by directory | `workdir`, `limit` |
| `opencode_session_show` | Inspect session metadata & transcript | `session`, `last_messages` |
| `opencode_session_delete` | Permanently remove a session | `session` |

---

## Agent Decision Flow

1. **Determine Interaction Type**:
   - **One-off task / Answer text needed**: Call `opencode_delegate(goal=..., workdir=...)` with default format (returns response text in `output`).
   - **Multi-turn / Iterative workflow**: Call `opencode_delegate(goal=..., format="json")` to capture `session_id`, then continue via `opencode_delegate(goal=..., session=session_id)`.
   - **Session Discovery**: Call `opencode_session_list(workdir=...)` to locate prior session IDs.
   - **Transcript Review**: Call `opencode_session_show(session=..., last_messages=10)` to inspect previous dialogue before continuing.

2. **Scope the Working Directory**:
   - Explicitly specify `workdir` whenever possible. Missing directories are auto-created.
   - For resumed sessions (`session="ses_..."`), the plugin automatically aligns the execution directory with the session's recorded creation directory.
   - Isolate concurrent delegations in separate working directories or temporary clones.

3. **Select Context Files**:
   - Pass relevant target files in `files=["path/to/file1", "path/to/file2"]` to focus OpenCode's context window.

---

## Core Execution Patterns

### Pattern 1: Bounded Feature or Bugfix
Delegate a self-contained change and return plain-text summary:
```python
opencode_delegate(
    goal="Implement exponential backoff retry in http_client.py and run pytest tests/test_client.py",
    workdir="/home/user/project",
    files=["http_client.py", "tests/test_client.py"],
    timeout=600
)
```
**Completion Criterion**: Tool returns `ok: true`. Verify changes with `git diff` or tests in the project directory.

### Pattern 2: Multi-Turn Iterative Development
Start a session, obtain its ID, and continue with iterative feedback:

**Turn 1: Initial Implementation (Request JSON)**
```python
res = opencode_delegate(
    goal="Scaffold auth module with JWT verification",
    workdir="/home/user/project",
    format="json"
)
session_id = res["session_id"]  # e.g., "ses_3b8a10f9"
```

**Turn 2: Follow-Up Refinement (Supply Session ID)**
```python
opencode_delegate(
    goal="Add refresh token rotation to the auth module and add unit tests",
    session=session_id
)
```
*(Alternatively, pass `continue=true` to continue the most recent session).*

### Pattern 3: Isolated PR or Code Review
Review uncommitted changes or branches in a temporary or isolated clone:
```python
opencode_delegate(
    goal="Review changes in this repository against main. Audit for security vulnerabilities, race conditions, and test gaps. Provide concrete diff recommendations.",
    workdir="/tmp/repo-review-worktree",
    files=["src/auth.py", "src/db.py"]
)
```

### Pattern 4: Session Inspection and Clean Up
Inspect a session's conversation history before resuming or deleting:
```python
# List existing sessions
sessions = opencode_session_list(limit=10)

# Inspect transcript of target session
details = opencode_session_show(session="ses_3b8a10f9", last_messages=5)

# Purge session when completed
opencode_session_delete(session="ses_3b8a10f9")
```

---

## Parameter Reference

| Parameter | Type | Default | Details |
|-----------|------|---------|---------|
| `goal` | string | *required* | Clear, actionable instruction for OpenCode. |
| `workdir` | string | cwd | Working directory. Auto-created if missing. Auto-aligned on session resumption. |
| `files` | list[str] | `[]` | File paths passed via `--file` to prime OpenCode's context. |
| `format` | string | `"default"` | Set to `"json"` to receive structured JSON (`session_id`, `tokens`, `cost`). Omit for text `output`. |
| `session` | string | `null` | Session ID (e.g. `ses_...`) to resume. Takes precedence over `continue`. |
| `continue`| bool | `false` | When true and `session` not given, resumes the most recent session. |
| `timeout` | int | `600` | Process timeout in seconds (clamped: 30–1800). |
| `model` | string | `null` | Override model (e.g., `openrouter/anthropic/claude-sonnet-4`). |
| `agent` | string | `null` | OpenCode agent mode (e.g., `build`, `plan`). |

---

## Response Shapes

### Default Plain-Text Format
```json
{
  "ok": true,
  "exit_code": 0,
  "output": "...OpenCode response text...",
  "error": null
}
```
*Use when you want to read or summarize OpenCode's direct assistant reply.*

### Structured JSON Format (`format="json"`)
```json
{
  "ok": true,
  "exit_code": 0,
  "session_id": "ses_3b8a10f9",
  "tokens": {"input": 1240, "output": 450},
  "cost": 0.0035,
  "stderr": "...",
  "error": null
}
```
*Use when capturing `session_id` for multi-turn sessions, or tracking token/cost budgets.*

---

## Critical Rules & Guardrails for Agents

1. **Verify on Disk**: Never take OpenCode's claims for granted. After `opencode_delegate` finishes with `ok: true`, check `git status`, inspect file modifications, and run test suites before marking your task complete.
2. **Handle Timeouts Gracefully**: On timeout, the tool returns `ok: false` with partial captured `output` and `error="Task timed out after ...s"`. If a task is complex, specify `timeout=1200` or `1800` rather than retrying immediately.
3. **Structured vs Text Tradeoff**:
   - `format="json"` exposes `session_id` but does not include conversational assistant text in `output`.
   - Default format includes conversational text in `output`, but omits `session_id`.
   - Standard pattern: Use `format="json"` on turn 1 to store `session_id`, and resume subsequent turns with plain text format to inspect results.
4. **Permanent Deletions**: `opencode_session_delete` permanently deletes the session from the OpenCode database (`~/.local/share/opencode/opencode.db`). Confirm the session ID with `opencode_session_show` before deletion.
5. **No Terminal Fallback**: Always invoke delegation via `opencode_delegate`. Do not invoke `opencode run` via bash/terminal commands.
