"""Unit tests for opencode-delegate plugin."""

from __future__ import annotations

import json
import os
import subprocess
from unittest.mock import MagicMock, patch

import pytest

import sys
from pathlib import Path

plugin_dir = str(Path(__file__).resolve().parent)
if plugin_dir not in sys.path:
    sys.path.insert(0, plugin_dir)

import schemas
import tools
from __init__ import register


def test_schema_structure():
    schema = schemas.OPENCODE_DELEGATE
    assert schema["name"] == "opencode_delegate"
    assert "description" in schema
    assert "parameters" in schema
    params = schema["parameters"]
    assert params["type"] == "object"
    assert "goal" in params["properties"]
    assert "workdir" in params["properties"]
    assert "timeout" in params["properties"]
    assert "model" in params["properties"]
    assert "goal" in params["required"]


def test_missing_or_empty_goal():
    for bad_args in [None, {}, {"goal": ""}, {"goal": "   "}, {"goal": None}]:
        res_raw = tools.opencode_delegate(bad_args)
        res = json.loads(res_raw)
        assert res["ok"] is False
        assert res["exit_code"] is None
        assert "goal" in res["error"]


def test_resolve_binary_via_which():
    with patch("shutil.which", return_value="/fake/bin/opencode"),          patch("os.path.isfile", return_value=True),          patch("os.access", return_value=True):
        bin_path = tools.resolve_opencode_binary()
        assert bin_path == "/fake/bin/opencode"


def test_resolve_binary_via_nvm_fallback():
    with patch("shutil.which", return_value=None),          patch("glob.glob", return_value=["/fake/nvm/v24.14.0/bin/opencode"]),          patch("os.path.isfile", return_value=True),          patch("os.access", return_value=True):
        bin_path = tools.resolve_opencode_binary()
        assert bin_path == "/fake/nvm/v24.14.0/bin/opencode"


def test_binary_not_found():
    with patch.object(tools, "resolve_opencode_binary", return_value=None):
        res = json.loads(tools.opencode_delegate({"goal": "test"}))
        assert res["ok"] is False
        assert "not installed or not found" in res["error"]


def test_invalid_workdir():
    with patch.object(tools, "resolve_opencode_binary", return_value="/fake/bin/opencode"):
        res = json.loads(tools.opencode_delegate({"goal": "test", "workdir": "/non/existent/path/xyz123"}))
        assert res["ok"] is False
        assert "Working directory does not exist" in res["error"]


def test_successful_run():
    mock_proc = MagicMock(returncode=0, stdout="Task completed successfully", stderr="")
    with patch.object(tools, "resolve_opencode_binary", return_value="/fake/bin/opencode"),          patch("subprocess.run", return_value=mock_proc) as mock_run:
        res_raw = tools.opencode_delegate({"goal": "write hello world"})
        res = json.loads(res_raw)
        assert res["ok"] is True
        assert res["exit_code"] == 0
        assert res["output"] == "Task completed successfully"
        assert res["error"] is None
        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args
        assert args[0] == ["/fake/bin/opencode", "run", "write hello world"]
        assert kwargs["shell"] is False


def test_command_with_model_flag():
    mock_proc = MagicMock(returncode=0, stdout="done", stderr="")
    with patch.object(tools, "resolve_opencode_binary", return_value="/fake/bin/opencode"),          patch("subprocess.run", return_value=mock_proc) as mock_run:
        res = json.loads(tools.opencode_delegate({"goal": "test", "model": "custom-vllm"}))
        assert res["ok"] is True
        args, _ = mock_run.call_args
        assert args[0] == ["/fake/bin/opencode", "run", "test", "--model", "custom-vllm"]


def test_timeout_clamping():
    mock_proc = MagicMock(returncode=0, stdout="ok", stderr="")
    with patch.object(tools, "resolve_opencode_binary", return_value="/fake/bin/opencode"),          patch("subprocess.run", return_value=mock_proc) as mock_run:
        
        # Below min (30)
        tools.opencode_delegate({"goal": "test", "timeout": 5})
        assert mock_run.call_args[1]["timeout"] == 30

        # Above max (1800)
        tools.opencode_delegate({"goal": "test", "timeout": 9999})
        assert mock_run.call_args[1]["timeout"] == 1800

        # Invalid string defaults to 600
        tools.opencode_delegate({"goal": "test", "timeout": "invalid"})
        assert mock_run.call_args[1]["timeout"] == 600


def test_timeout_expired():
    with patch.object(tools, "resolve_opencode_binary", return_value="/fake/bin/opencode"), \
         patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd=["opencode"], timeout=30, output="partial output")):
        res = json.loads(tools.opencode_delegate({"goal": "test", "timeout": 30}))
        assert res["ok"] is False
        assert res["exit_code"] is None
        assert "timed out after 30 seconds" in res["error"]
        assert res["output"] == "partial output"


def test_file_not_found_on_exec():
    with patch.object(tools, "resolve_opencode_binary", return_value="/fake/bin/opencode"),          patch("subprocess.run", side_effect=FileNotFoundError("No such file")):
        res = json.loads(tools.opencode_delegate({"goal": "test"}))
        assert res["ok"] is False
        assert "binary not found" in res["error"]


def test_output_truncation():
    long_output = "A" * 5000 + "B" * 5000  # 10,000 chars
    mock_proc = MagicMock(returncode=0, stdout=long_output, stderr="")
    with patch.object(tools, "resolve_opencode_binary", return_value="/fake/bin/opencode"),          patch("subprocess.run", return_value=mock_proc):
        res = json.loads(tools.opencode_delegate({"goal": "test"}))
        assert len(res["output"]) == 8000
        assert res["output"].startswith("A" * 3000)
        assert res["output"].endswith("B" * 5000)


def test_registration():
    mock_ctx = MagicMock()
    register(mock_ctx)
    mock_ctx.register_tool.assert_called_once_with(
        name="opencode_delegate",
        toolset="opencode-delegate",
        schema=schemas.OPENCODE_DELEGATE,
        handler=tools.opencode_delegate,
    )
