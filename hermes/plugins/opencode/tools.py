"""Handlers for the opencode-delegate plugin tools."""

from __future__ import annotations

import glob
import json
import os
import shutil
import signal
import sqlite3
import subprocess
from typing import Any

TRUNCATION_LIMIT = 8000
DEFAULT_TIMEOUT = 300
MIN_TIMEOUT = 30
MAX_TIMEOUT = 1800
SESSION_TIMEOUT = 60


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

    home_candidate = os.path.expanduser("~/.opencode/bin/opencode")
    if os.path.isfile(home_candidate) and os.access(home_candidate, os.X_OK):
        return home_candidate

    return None


def get_opencode_db_path() -> str:
    """Return default path to opencode SQLite database."""
    xdg_data = os.environ.get("XDG_DATA_HOME")
    if xdg_data:
        return os.path.join(os.path.expanduser(xdg_data), "opencode", "opencode.db")
    return os.path.expanduser("~/.local/share/opencode/opencode.db")



def _get_session_dir(session_id: str) -> str | None:
    """Look up the recorded directory for an OpenCode session.

    First checks OpenCode's local SQLite database. If unavailable or not found,
    falls back to CLI export. Returns the resolved directory if it exists on disk, else None.
    """
    if not session_id or not isinstance(session_id, str):
        return None
    session_id = session_id.strip()
    if not session_id:
        return None

    # Fast path: SQLite query
    db_path = get_opencode_db_path()
    if os.path.isfile(db_path):
        try:
            with sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=2.0) as conn:
                cursor = conn.cursor()
                row = cursor.execute("SELECT directory FROM session WHERE id = ?", (session_id,)).fetchone()
                if row and row[0] and isinstance(row[0], str):
                    cand = os.path.abspath(os.path.expanduser(row[0].strip()))
                    if os.path.isdir(cand):
                        return cand
        except Exception:
            pass

    # Fallback: CLI export
    try:
        ret, stdout, _ = _run_cli(["export", session_id], timeout=10)
        if ret == 0 and stdout:
            start = stdout.find("{")
            if start != -1:
                data = json.loads(stdout[start:])
                directory = data.get("info", {}).get("directory")
                if directory and isinstance(directory, str):
                    cand = os.path.abspath(os.path.expanduser(directory.strip()))
                    if os.path.isdir(cand):
                        return cand
    except Exception:
        pass

    return None


def _run_cli(cmd: list[str], timeout: int = SESSION_TIMEOUT, cwd: str | None = None) -> tuple[int | None, str, str]:
    """Run the opencode CLI and return (returncode, stdout, stderr)."""
    bin_path = resolve_opencode_binary()
    if not bin_path:
        return None, "", "opencode CLI is not installed or not found on PATH or in ~/.nvm/versions/node/*/bin/opencode or ~/.opencode/bin/opencode"

    env = os.environ.copy()
    bin_dir = os.path.dirname(bin_path)
    current_path = env.get("PATH", "")
    if bin_dir not in current_path.split(os.pathsep):
        env["PATH"] = f"{bin_dir}{os.pathsep}{current_path}"

    full_cmd = [bin_path] + cmd
    try:
        proc = subprocess.run(
            full_cmd,
            cwd=cwd,
            env=env,
            stdin=subprocess.DEVNULL,
            timeout=timeout,
            capture_output=True,
            text=True,
            shell=False,
            start_new_session=True,
        )
    except subprocess.TimeoutExpired:
        return None, "", f"Execution timed out after {timeout} seconds"
    except FileNotFoundError:
        return None, "", "opencode CLI binary not found or executable cannot be invoked"
    return proc.returncode, proc.stdout or "", proc.stderr or ""


def _error(error: str) -> str:
    return json.dumps({"ok": False, "error": error})


def opencode_delegate(args: dict[str, Any] | None, **kwargs: Any) -> str:
    """Delegate a coding task to OpenCode CLI (opencode run).

    Parameters:
        args: Dictionary containing:
            - goal (str, required): Task description for OpenCode.
            - workdir (str, optional): Target working directory (default: current working directory).
            - timeout (int, optional): Timeout in seconds (default: 600, clamped 30-1800).
            - model (str, optional): Model name passed via --model.
            - agent (str, optional): Agent name passed via --agent.
            - files (list[str], optional): File paths passed via --file.
            - session (str, optional): Session ID to continue via --session.
            - continue (bool, optional): Continue the last session via --continue.
            - format (str, optional): "json" for structured output with session_id,
              tokens, and cost; default is plain text output.
        **kwargs: Additional keyword arguments for forward compatibility.

    Returns:
        JSON string conforming to:
        {"ok": bool, "exit_code": int | None, "output": str, "error": str | None}
        or, when format is "json":
        {"ok": bool, "exit_code": int | None, "session_id": str | None,
         "tokens": object | None, "cost": number | None,
         "stderr": str | None, "error": str | None}
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
        session = args.get("session")
        session_id = session.strip() if session and isinstance(session, str) else None

        # Auto-align working directory with the session's recorded creation directory.
        # This is critical to prevent OpenCode CLI instance mismatch hangs when resuming sessions.
        session_dir = _get_session_dir(session_id) if session_id else None
        if session_dir:
            cwd = session_dir
        elif workdir and isinstance(workdir, str) and workdir.strip():
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

        agent = args.get("agent")
        if agent and isinstance(agent, str) and agent.strip():
            cmd.extend(["--agent", agent.strip()])

        files = args.get("files")
        if isinstance(files, list):
            for file_item in files:
                if isinstance(file_item, str) and file_item.strip():
                    cmd.extend(["--file", file_item.strip()])

        if session_id:
            cmd.extend(["--session", session_id])
        elif args.get("continue") is True:
            cmd.append("--continue")

        use_json = args.get("format") == "json"
        if use_json:
            cmd.extend(["--format", "json"])

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
                stdin=subprocess.DEVNULL,
                timeout=timeout,
                capture_output=True,
                text=True,
                shell=False,
                start_new_session=True,
            )
        except subprocess.TimeoutExpired as exc:
            partial_out = exc.stdout or ""
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

        exit_code = proc.returncode
        stdout = proc.stdout or ""
        stderr = proc.stderr or ""

        if use_json:
            session_id_out = None
            tokens = None
            cost = None
            for line in stdout.splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(event, dict):
                    continue
                part = event.get("part")
                if isinstance(part, dict):
                    if part.get("sessionID"):
                        session_id_out = part["sessionID"]
                    if event.get("type") == "step_finish":
                        tokens = part.get("tokens")
                        cost = part.get("cost")
            result: dict[str, Any] = {
                "ok": exit_code == 0,
                "exit_code": exit_code,
                "session_id": session_id_out,
                "tokens": tokens,
                "cost": cost,
            }
            if stderr:
                result["stderr"] = stderr
            if exit_code != 0:
                result["error"] = stderr.strip() or f"Process exited with non-zero code {exit_code}"
            return json.dumps(result)

        combined = stdout
        if stderr:
            if combined:
                combined = f"{combined}\n{stderr}"
            else:
                combined = stderr

        if len(combined) > TRUNCATION_LIMIT:
            combined = combined[-TRUNCATION_LIMIT:]

        ok = (exit_code == 0)
        error_msg = None
        if not ok:
            error_msg = stderr.strip() or f"Process exited with non-zero code {exit_code}"

        return json.dumps({
            "ok": ok,
            "exit_code": exit_code,
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


def opencode_session_list(args: dict[str, Any] | None, **kwargs: Any) -> str:
    """List OpenCode sessions.

    Parameters:
        args: Dictionary containing:
            - limit (int, optional): Max sessions to return (default: 20).
            - workdir (str, optional): Filter sessions by directory.
        **kwargs: Additional keyword arguments for forward compatibility.

    Returns:
        JSON string: {"ok": bool, "sessions": list, "error": str | None}
        Each session: {"id", "title", "updated", "created", "directory"}
    """
    try:
        limit = 20
        raw_limit = args.get("limit") if isinstance(args, dict) else None
        if raw_limit is not None:
            try:
                limit = int(raw_limit)
            except (ValueError, TypeError):
                limit = 20
        limit = min(max(limit, 1), 100)

        returncode, stdout, stderr = _run_cli(["session", "list", "--format", "json", "-n", str(limit)])
        if returncode is None:
            return _error(stderr)
        if returncode != 0:
            return _error(stderr.strip() or f"opencode session list exited with code {returncode}")

        try:
            sessions = json.loads(stdout)
        except json.JSONDecodeError:
            return _error("Failed to parse opencode session list output")

        if not isinstance(sessions, list):
            return _error("Unexpected opencode session list output")

        workdir = args.get("workdir") if isinstance(args, dict) else None
        if workdir and isinstance(workdir, str) and workdir.strip():
            workdir = os.path.abspath(os.path.expanduser(workdir.strip()))
            sessions = [s for s in sessions if isinstance(s, dict) and s.get("directory") == workdir]

        return json.dumps({"ok": True, "sessions": sessions, "error": None})

    except Exception as exc:
        return _error(f"Unexpected execution failure: {str(exc)}")


def opencode_session_show(args: dict[str, Any] | None, **kwargs: Any) -> str:
    """Show details and transcript of an OpenCode session.

    Parameters:
        args: Dictionary containing:
            - session (str, required): Session ID to inspect.
            - last_messages (int, optional): Number of recent messages to include (default: 10).
        **kwargs: Additional keyword arguments for forward compatibility.

    Returns:
        JSON string: {"ok": bool, "session": object, "messages": list, "error": str | None}
    """
    try:
        if not isinstance(args, dict):
            return _error("Missing or empty required parameter: 'session'")
        session = args.get("session")
        if not session or not isinstance(session, str) or not session.strip():
            return _error("Missing or empty required parameter: 'session'")
        session = session.strip()

        last_messages = 10
        raw_last = args.get("last_messages")
        if raw_last is not None:
            try:
                last_messages = int(raw_last)
            except (ValueError, TypeError):
                last_messages = 10
        last_messages = min(max(last_messages, 1), 100)

        returncode, stdout, stderr = _run_cli(["export", session])
        if returncode is None:
            return _error(stderr)
        if returncode != 0:
            return _error(stderr.strip() or f"opencode export exited with code {returncode}")

        try:
            raw = stdout
            start = raw.index("{")
            data = json.loads(raw[start:])
        except (ValueError, json.JSONDecodeError):
            return _error("Failed to parse opencode export output")

        if not isinstance(data, dict) or "info" not in data:
            return _error("Unexpected opencode export output")

        messages = data.get("messages", [])
        if not isinstance(messages, list):
            messages = []

        def _extract_text(message: dict[str, Any]) -> str:
            parts = message.get("parts", [])
            texts = []
            for part in parts:
                if isinstance(part, dict) and part.get("type") == "text" and isinstance(part.get("text"), str):
                    texts.append(part["text"])
            return "\n".join(texts)

        recent = messages[-last_messages:]
        simplified = []
        for message in recent:
            info = message.get("info", {}) if isinstance(message, dict) else {}
            simplified.append({
                "role": info.get("role"),
                "text": _extract_text(message) if isinstance(message, dict) else "",
                "created": info.get("time", {}).get("created") if isinstance(info.get("time"), dict) else None,
            })

        return json.dumps({
            "ok": True,
            "session": data.get("info"),
            "messages": simplified,
            "error": None,
        })

    except Exception as exc:
        return _error(f"Unexpected execution failure: {str(exc)}")


def opencode_session_delete(args: dict[str, Any] | None, **kwargs: Any) -> str:
    """Delete an OpenCode session.

    Parameters:
        args: Dictionary containing:
            - session (str, required): Session ID to delete.
        **kwargs: Additional keyword arguments for forward compatibility.

    Returns:
        JSON string: {"ok": bool, "error": str | None}
    """
    try:
        if not isinstance(args, dict):
            return _error("Missing or empty required parameter: 'session'")
        session = args.get("session")
        if not session or not isinstance(session, str) or not session.strip():
            return _error("Missing or empty required parameter: 'session'")
        session = session.strip()

        returncode, stdout, stderr = _run_cli(["session", "delete", session])
        if returncode is None:
            return _error(stderr)
        if returncode != 0:
            return _error(stderr.strip() or f"opencode session delete exited with code {returncode}")

        return json.dumps({"ok": True, "error": None})

    except Exception as exc:
        return _error(f"Unexpected execution failure: {str(exc)}")
