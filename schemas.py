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

OPENCODE_SESSION_LIST = {
    "name": "opencode_session_list",
    "description": (
        "List OpenCode sessions, most recent first. Use to find session IDs "
        "for resuming a previous OpenCode conversation. Optionally filter by "
        "working directory."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "limit": {
                "type": "integer",
                "description": "Max sessions to return (default 20, max 100)",
            },
            "workdir": {
                "type": "string",
                "description": "Only list sessions created in this directory",
            },
        },
        "required": [],
    },
}

OPENCODE_SESSION_SHOW = {
    "name": "opencode_session_show",
    "description": (
        "Show details and recent transcript of an OpenCode session. Use to "
        "inspect what happened in a session before resuming it."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "session": {
                "type": "string",
                "description": "Session ID to inspect",
            },
            "last_messages": {
                "type": "integer",
                "description": "Number of recent messages to include (default 10, max 100)",
            },
        },
        "required": ["session"],
    },
}

OPENCODE_SESSION_DELETE = {
    "name": "opencode_session_delete",
    "description": (
        "Delete an OpenCode session by ID. Permanent; cannot be undone."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "session": {
                "type": "string",
                "description": "Session ID to delete",
            },
        },
        "required": ["session"],
    },
}
