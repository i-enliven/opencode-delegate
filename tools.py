"""Handler for the opencode_delegate tool."""

from __future__ import annotations

import glob
import json
import os
import shutil
import subprocess
from typing import Any

TRUNCATION_LIMIT = 8000
DEFAULT_TIMEOUT = 600
MIN_TIMEOUT = 30
MAX_TIMEOUT = 1800


def resolve_opencode_binary() -> str | None:
    """Resolve the path to the opencode executable.

    Tries PATH first via shutil.which, then checks nvm node version directories.
    Returns the absolute path if found and executable, or None.
    """
    which_path = shutil.which("opencode")
    if which_path and os.path.isfile(which_path) and os.access(which_path, os.X_OK):
        return which_path

    nvm_pattern = os.path.expanduser("~/.nvm/versions/node/*/bin/opencode")
    candidates = sorted(glob.glob(nvm_pattern), reverse=True)
    for candidate in candidates:
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate

    return None


def opencode_delegate(args: dict[str, Any] | None, **kwargs: Any) -> str:
    """Delegate a coding task to OpenCode CLI (opencode run).

    Parameters:
        args: Dictionary containing:
            - goal (str, required): Task description for OpenCode.
            - workdir (str, optional): Target working directory (default: current working directory).
            - timeout (int, optional): Timeout in seconds (default: 600, clamped 30-1800).
            - model (str, optional): Model name passed via --model.
        **kwargs: Additional keyword arguments for forward compatibility.

    Returns:
        JSON string conforming to:
        {"ok": bool, "exit_code": int | None, "output": str, "error": str | None}
    """
    try:
        if not isinstance(args, dict):
            return json.dumps({
                "ok": False,
                "exit_code": None,
                "output": "",
                "error": "Missing or empty required parameter: 'goal'",
            })

        goal = args.get("goal")
        if not goal or not isinstance(goal, str) or not goal.strip():
            return json.dumps({
                "ok": False,
                "exit_code": None,
                "output": "",
                "error": "Missing or empty required parameter: 'goal'",
            })
        goal = goal.strip()

        bin_path = resolve_opencode_binary()
        if not bin_path:
            return json.dumps({
                "ok": False,
                "exit_code": None,
                "output": "",
                "error": "opencode CLI is not installed or not found on PATH or in ~/.nvm/versions/node/*/bin/opencode",
            })

        workdir = args.get("workdir")
        if workdir and isinstance(workdir, str) and workdir.strip():
            cwd = os.path.abspath(os.path.expanduser(workdir.strip()))
        else:
            cwd = os.getcwd()

        if not os.path.isdir(cwd):
            try:
                os.makedirs(cwd, exist_ok=True)
            except OSError as makedirs_error:
                return json.dumps({
                    "ok": False,
                    "exit_code": None,
                    "output": "",
                    "error": f"Working directory does not exist and could not be created: {cwd} ({makedirs_error})",
                })

        try:
            raw_timeout = args.get("timeout")
            timeout_val = DEFAULT_TIMEOUT if raw_timeout is None else int(raw_timeout)
        except (ValueError, TypeError):
            timeout_val = DEFAULT_TIMEOUT
        timeout = min(max(timeout_val, MIN_TIMEOUT), MAX_TIMEOUT)

        cmd = [bin_path, "run", "--dir", cwd, goal]
        model = args.get("model")
        if model and isinstance(model, str) and model.strip():
            cmd.extend(["--model", model.strip()])

        env = os.environ.copy()
        bin_dir = os.path.dirname(bin_path)
        current_path = env.get("PATH", "")
        if bin_dir not in current_path.split(os.pathsep):
            env["PATH"] = f"{bin_dir}{os.pathsep}{current_path}"

        try:
            proc = subprocess.run(
                cmd,
                cwd=cwd,
                env=env,
                timeout=timeout,
                capture_output=True,
                text=True,
                shell=False,
            )
        except subprocess.TimeoutExpired as exc:
            partial_out = exc.stdout or ""
            if isinstance(partial_out, bytes):
                partial_out = partial_out.decode("utf-8", errors="replace")
            if len(partial_out) > TRUNCATION_LIMIT:
                partial_out = partial_out[-TRUNCATION_LIMIT:]
            return json.dumps({
                "ok": False,
                "exit_code": None,
                "output": partial_out,
                "error": f"Execution timed out after {timeout} seconds",
            })
        except FileNotFoundError:
            return json.dumps({
                "ok": False,
                "exit_code": None,
                "output": "",
                "error": "opencode CLI binary not found or executable cannot be invoked",
            })

        stdout = proc.stdout or ""
        stderr = proc.stderr or ""
        combined = stdout
        if stderr:
            if combined:
                combined = f"{combined}\n{stderr}"
            else:
                combined = stderr

        if len(combined) > TRUNCATION_LIMIT:
            combined = combined[-TRUNCATION_LIMIT:]

        ok = (proc.returncode == 0)
        error_msg = None
        if not ok:
            error_msg = stderr.strip() or f"Process exited with non-zero code {proc.returncode}"

        return json.dumps({
            "ok": ok,
            "exit_code": proc.returncode,
            "output": combined,
            "error": error_msg,
        })

    except Exception as exc:
        return json.dumps({
            "ok": False,
            "exit_code": None,
            "output": "",
            "error": f"Unexpected execution failure: {str(exc)}",
        })
