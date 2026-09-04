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
        },
        "required": ["goal"],
    },
}
