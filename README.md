# opencode-delegate

A Hermes plugin that delegates bounded coding tasks to the [OpenCode CLI](https://opencode.ai) and manages OpenCode sessions, via four tools: `opencode_delegate`, `opencode_session_list`, `opencode_session_show`, and `opencode_session_delete`.

## What it does

Runs `opencode run` as a subprocess with your goal, working directory, and options, then returns OpenCode's final report as JSON. OpenCode is an autonomous coding agent — this plugin lets another agent (or your tooling) hand off bounded tasks like "implement feature X", "fix bug Y", or "review this module" and get back a structured result. Session tools let you list, inspect, resume, and delete OpenCode sessions.

## Installation

1. Install OpenCode CLI (one of these locations is auto-detected):
   - On `PATH` (`opencode`)
   - `~/.nvm/versions/node/*/bin/opencode` (nvm-managed installs)
   - `~/.opencode/bin/opencode` (standard install script location)

2. Install the plugin into your Hermes plugin directory (or any directory Hermes loads plugins from):

   ```bash
   git clone https://github.com/i-enliven/opencode-delegate.git
   ```

   The repo ships `plugin.yaml`, which declares the tool `opencode_delegate`.

## Tool usage

Call `opencode_delegate` with a dict of arguments:

```json
{
  "goal": "Add retry logic to API calls and update tests",
  "workdir": "~/projects/my-app",
  "timeout": 900,
  "model": "openrouter/anthropic/claude-sonnet-4",
  "agent": "build",
  "files": ["src/api/client.py", "tests/test_client.py"],
  "session": "ses_abc123",
  "continue": false,
  "format": "json"
}
```

### Parameters

| Parameter  | Type       | Required | Description |
|------------|------------|----------|-------------|
| `goal`     | string     | yes      | The coding task for OpenCode |
| `workdir`  | string     | no       | Working directory for the task (default: session cwd). Created if missing |
| `timeout`  | integer    | no       | Seconds to allow; default 600, clamped to 30–1800 |
| `model`    | string     | no       | Force a specific model via `--model` |
| `agent`    | string     | no       | Agent name passed via `--agent` (e.g. `build`, `plan`) |
| `files`    | string[]   | no       | File paths to attach as context via `--file` |
| `session`  | string     | no       | Session ID to continue via `--session` (takes precedence over `continue`) |
| `continue` | boolean    | no       | Continue the last session via `--continue` |
| `format`   | string     | no       | Set to `json` for structured output (session_id, tokens, cost) |

### Response format

Default (plain text):

```json
{"ok": true, "exit_code": 0, "output": "...", "error": null}
```

With `"format": "json"`:

```json
{
  "ok": true,
  "exit_code": 0,
  "session_id": "ses_f8c27c15effePSLs7H19SlyT1T",
  "tokens": {"input": 0, "output": 0, "reasoning": 0, "cache": {"write": 0, "read": 0}},
  "cost": 0
}
```

The `session_id` from a JSON-format run can be passed back as `session` to continue that conversation in a follow-up call.

## Session tools

### opencode_session_list

List OpenCode sessions, most recent first:

```json
{"limit": 20, "workdir": "~/projects/my-app"}
```

Both parameters are optional (`limit` default 20, clamped 1–100; `workdir` is an exact-match filter on the session's directory). Returns `{"ok": true, "sessions": [{"id", "title", "updated", "created", "directory"}]}`.

### opencode_session_show

Show a session's details and recent transcript (via `opencode export`):

```json
{"session": "ses_abc123", "last_messages": 10}
```

Returns `{"ok": true, "session": {...}, "messages": [{"role", "text", "created"}]}` (`last_messages` default 10, clamped 1–100).

### opencode_session_delete

Delete a session permanently:

```json
{"session": "ses_abc123"}
```

Returns `{"ok": true}`.

## Behavior notes

- Output is truncated to the last 8000 characters.
- Timeouts are clamped between 30 and 1800 seconds.
- A missing `workdir` is pre-created (`makedirs(exist_ok=True)`).
- The subprocess PATH is augmented with the resolved binary's directory so child processes can find sibling tools.
- All failures return `{"ok": false, ...}` with a descriptive `error` — the handler never raises.

## Bundled skill

The repo also ships a Hermes skill file at `skills/opencode/SKILL.md` — a usage guide for OpenCode CLI covering one-shot tasks, interactive sessions, PR review workflows, parallel work patterns, and common flags. Copy it into your skills directory (e.g. `~/.agents/skills/opencode/SKILL.md`) to make it available to your agent:

```bash
cp skills/opencode/SKILL.md ~/.agents/skills/opencode/SKILL.md
```

## Development

Run the test suite:

```bash
python -m pytest test_opencode_delegate.py -v
```

## License

MIT
