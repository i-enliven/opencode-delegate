# opencode-delegate

A Hermes plugin that delegates bounded coding tasks to the [OpenCode CLI](https://opencode.ai) and manages OpenCode sessions, via four tools: `opencode_delegate`, `opencode_session_list`, `opencode_session_show`, and `opencode_session_delete`.

## What it does

Runs `opencode run` as a subprocess with your goal, working directory, and options, then returns OpenCode's final report as JSON. OpenCode is an autonomous coding agent — this plugin lets another agent (or your tooling) hand off bounded tasks like "implement feature X", "fix bug Y", or "review this module" and get back a structured result. Session tools let you list, inspect, resume, and delete OpenCode sessions.

## Repository Structure

The repository is structured to map directly to Hermes' configuration directory (`~/.hermes/`):

```
opencode-delegate/
├── hermes/
│   ├── plugins/
│   │   └── opencode/
│   │       ├── __init__.py
│   │       ├── plugin.yaml
│   │       ├── schemas.py
│   │       └── tools.py
│   └── skills/
│       └── opencode/
│           └── SKILL.md
├── test_opencode_delegate.py
└── README.md
```

## Installation

### 1. Install OpenCode CLI
Ensure the OpenCode CLI is installed (auto-detected in any of these locations):
- On `PATH` (`opencode`)
- `~/.nvm/versions/node/*/bin/opencode` (nvm-managed installs)
- `~/.opencode/bin/opencode` (standard install script location)

### 2. Clone the Repository
```bash
git clone https://github.com/i-enliven/opencode-delegate.git
cd opencode-delegate
```

### 3. Install the Plugin in Hermes

**Option A: Copy files into Hermes**
```bash
mkdir -p ~/.hermes/plugins
cp -r hermes/plugins/opencode ~/.hermes/plugins/
```

**Option B: Symlink (Recommended if you keep the repo updated)**
```bash
mkdir -p ~/.hermes/plugins
ln -s "$(pwd)/hermes/plugins/opencode" ~/.hermes/plugins/opencode
```

**Enable the plugin in Hermes**:
Add `opencode` to `plugins.enabled` in `~/.hermes/config.yaml`:
```yaml
plugins:
  enabled:
    - opencode
```
Or enable it via the Hermes CLI:
```bash
hermes plugins enable opencode
```

The plugin declares four tools: `opencode_delegate`, `opencode_session_list`, `opencode_session_show`, and `opencode_session_delete`.

### 4. Install the Skill in Hermes
The repo ships a Hermes skill file at `hermes/skills/opencode/SKILL.md` covering CLI workflows, prompts, and tool patterns:

**Option A: Copy the skill file**
```bash
mkdir -p ~/.hermes/skills
cp -r hermes/skills/opencode ~/.hermes/skills/
```

**Option B: Symlink the skill (automatically tracks updates)**
```bash
mkdir -p ~/.hermes/skills
ln -s "$(pwd)/hermes/skills/opencode" ~/.hermes/skills/opencode
```

*(For generic agent environments using `~/.agents/`, copy to `~/.agents/skills/opencode/`)*.

---

### Quick Install (One-Liner)
To install both the plugin and skill without keeping the cloned repo:
```bash
git clone https://github.com/i-enliven/opencode-delegate.git /tmp/opencode-delegate && \
  mkdir -p ~/.hermes/plugins ~/.hermes/skills && \
  cp -r /tmp/opencode-delegate/hermes/plugins/opencode ~/.hermes/plugins/ && \
  cp -r /tmp/opencode-delegate/hermes/skills/opencode ~/.hermes/skills/ && \
  rm -rf /tmp/opencode-delegate && \
  hermes plugins enable opencode
```
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
- Standard input is detached (`stdin=subprocess.DEVNULL`) to prevent blocking on non-interactive executions.
- A missing `workdir` is pre-created (`makedirs(exist_ok=True)`).
- The subprocess PATH is augmented with the resolved binary's directory so child processes can find sibling tools.
- All failures return `{"ok": false, ...}` with a descriptive `error` — the handler never raises.

## Using the Skill with Hermes & AI Agents

The repository ships an agent-optimized skill file at `hermes/skills/opencode/SKILL.md`. This skill equips AI agents (like Hermes, Claude, or custom agentic workflows) with the decision logic, execution patterns, and guardrails necessary to autonomously delegate tasks to OpenCode. See [Installation](#4-install-the-skill-in-hermes) above for copying or symlinking it into `~/.hermes/skills/opencode/SKILL.md`.

### How Hermes & Agents Discover the Skill
Hermes indexes installed skills in `~/.hermes/skills/` at session startup:
1. The skill frontmatter registers `opencode` with trigger tags (`Coding-Agent`, `OpenCode`, `Autonomous`, `Refactoring`, `Code-Review`).
2. When a prompt requires coding, fixing bugs, refactoring, or code reviews, the agent runtime matches the prompt intent against the skill description and activates it into context.
3. You can inspect all available skills in Hermes with:
   ```bash
   hermes skills list
   ```

### Prompting Hermes to Delegate to OpenCode
Users can instruct Hermes in natural language to leverage OpenCode. Hermes references the skill to invoke the appropriate plugin tools and parameters:

- **One-Shot Implementation / Bug Fix**:
  > *"Use OpenCode to implement exponential backoff retry in `http_client.py` and run tests."*
- **Iterative Development & Feedback**:
  > *"Delegate creating a FastAPI authentication boilerplate to OpenCode."*  
  Followed by:  
  > *"Ask OpenCode to continue that session and add JWT refresh token rotation."*
- **Targeted Code & PR Review**:
  > *"Use OpenCode to review the uncommitted changes in this repository for potential race conditions."*
- **Session Management**:
  > *"List my recent OpenCode sessions and delete the ones from yesterday."*

### Agent Delegation Lifecycle
When the skill is active, agents follow this structured lifecycle:
1. **Scope & Prepare**: The agent determines if the task is one-shot or multi-turn, scopes the `workdir`, and specifies relevant context files (`files=[...]`).
2. **Execute Delegation**: The agent invokes `opencode_delegate` (using `format="json"` when multi-turn session tracking is required).
3. **Session Continuation**: For follow-up tasks, the agent feeds `session="ses_..."` back into `opencode_delegate`. The plugin automatically aligns the execution directory with the session's creation path.
4. **Independent Disk Verification**: Before reporting success to the user, the agent inspects the file modifications (`git diff`, `git status`) and executes automated tests on disk.

## Development

Run the test suite:

```bash
python -m pytest test_opencode_delegate.py -v
```

## License

MIT
