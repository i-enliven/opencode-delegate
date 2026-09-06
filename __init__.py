"""Hermes plugin to delegate coding work to OpenCode CLI."""

from __future__ import annotations

try:
    from . import schemas, tools
except ImportError:
    import schemas, tools


def register(ctx):
    """Register the opencode-delegate tools with Hermes."""
    ctx.register_tool(
        name="opencode_delegate",
        toolset="opencode-delegate",
        schema=schemas.OPENCODE_DELEGATE,
        handler=tools.opencode_delegate,
    )
    ctx.register_tool(
        name="opencode_session_list",
        toolset="opencode-delegate",
        schema=schemas.OPENCODE_SESSION_LIST,
        handler=tools.opencode_session_list,
    )
    ctx.register_tool(
        name="opencode_session_show",
        toolset="opencode-delegate",
        schema=schemas.OPENCODE_SESSION_SHOW,
        handler=tools.opencode_session_show,
    )
    ctx.register_tool(
        name="opencode_session_delete",
        toolset="opencode-delegate",
        schema=schemas.OPENCODE_SESSION_DELETE,
        handler=tools.opencode_session_delete,
    )
