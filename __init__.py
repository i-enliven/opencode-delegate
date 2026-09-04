"""Hermes plugin to delegate coding work to OpenCode CLI."""

from __future__ import annotations

try:
    from . import schemas, tools
except ImportError:
    import schemas, tools


def register(ctx):
    """Register the opencode_delegate tool with Hermes."""
    ctx.register_tool(
        name="opencode_delegate",
        toolset="opencode-delegate",
        schema=schemas.OPENCODE_DELEGATE,
        handler=tools.opencode_delegate,
    )
