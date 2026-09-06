"""Tool schemas for opencode-delegate plugin."""

from __future__ import annotations

OPENCODE_DELEGATE = {
    "name": "opencode_delegate",
    "description": (
        "Delegate a bounded coding task to OpenCode CLI. OpenCode is an "
        "autonomous coding agent configured with a local vLLM backend. Use "
        "for implementing features, fixing bugs, or reviewing code when "
        "explicitly requested or when an external coding agent is preferred. "
        "Returns OpenCode's final report as text."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "goal": {
                "type": "string",
                "description": "The coding task for OpenCode",
            },
            "workdir": {
                "type": "string",
                "description": "Working directory for the task (default: session cwd)",
            },
            "timeout": {
                "type": "integer",
                "description": "Seconds to allow, default 600, max 1800",
            },
            "model": {
                "type": "string",
                "description": "Force a specific model via --model flag",
            },
            "agent": {
                "type": "string",
                "description": "Agent name passed via --agent flag",
            },
            "files": {
                "type": "array",
                "items": {"type": "string"},
                "description": "File paths to attach as context via --file flag",
            },
            "session": {
                "type": "string",
                "description": "Session ID to continue via --session flag",
            },
            "continue": {
                "type": "boolean",
                "description": "Continue the last session via --continue flag",
            },
            "format": {
                "type": "string",
                "description": "Set to 'json' for structured output (session_id, tokens, cost)",
            },
        },
        "required": ["goal"],
    },
}
