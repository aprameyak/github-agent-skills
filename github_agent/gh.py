"""Thin wrapper around the authenticated GitHub CLI (`gh`)."""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from typing import Any


class GhError(RuntimeError):
    """Raised when a `gh` invocation fails."""

    def __init__(self, message: str, *, command: list[str], stderr: str = "", returncode: int = 1):
        super().__init__(message)
        self.command = command
        self.stderr = stderr
        self.returncode = returncode


@dataclass(frozen=True)
class AuthStatus:
    logged_in: bool
    host: str
    username: str | None
    protocol: str | None
    scopes: list[str]
    message: str


def gh_available() -> bool:
    return shutil.which("gh") is not None


def run_gh(
    args: list[str],
    *,
    timeout: int = 120,
    check: bool = True,
    input_text: str | None = None,
) -> subprocess.CompletedProcess[str]:
    if not gh_available():
        raise GhError(
            "GitHub CLI (`gh`) was not found on PATH. Install it from https://cli.github.com/",
            command=["gh", *args],
        )
    command = ["gh", *args]
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            input=input_text,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise GhError(f"Command timed out after {timeout}s", command=command) from exc

    if check and result.returncode != 0:
        stderr = (result.stderr or "").strip()
        raise GhError(
            stderr or f"gh exited with code {result.returncode}",
            command=command,
            stderr=stderr,
            returncode=result.returncode,
        )
    return result


def run_gh_json(args: list[str], *, timeout: int = 120) -> Any:
    result = run_gh(args, timeout=timeout)
    text = (result.stdout or "").strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise GhError(
            f"Failed to parse JSON from gh: {exc}",
            command=["gh", *args],
            stderr=result.stdout[:500],
        ) from exc


def api(
    path: str,
    *,
    method: str = "GET",
    fields: dict[str, str] | None = None,
    raw_fields: dict[str, str] | None = None,
    jq: str | None = None,
    paginate: bool = False,
    input_json: Any | None = None,
    timeout: int = 180,
) -> Any:
    if method == "GET" and paginate and jq is None and fields is None and raw_fields is None and input_json is None:
        return _api_paginate(path, timeout=timeout)

    args = ["api", path, "--method", method]
    if paginate:
        args.append("--paginate")
    if jq:
        args.extend(["--jq", jq])
    if fields:
        for key, value in fields.items():
            args.extend(["-f", f"{key}={value}"])
    if raw_fields:
        for key, value in raw_fields.items():
            args.extend(["-F", f"{key}={value}"])
    input_text = None
    if input_json is not None:
        args.extend(["--input", "-"])
        input_text = json.dumps(input_json)
        result = run_gh(args, timeout=timeout, input_text=input_text)
        text = (result.stdout or "").strip()
        if not text:
            return None
        return json.loads(text)
    return run_gh_json(args, timeout=timeout)


def _api_paginate(path: str, *, timeout: int = 180) -> list[Any]:
    """Paginate list endpoints that return JSON arrays."""
    result = run_gh(["api", path, "--paginate"], timeout=timeout)
    text = (result.stdout or "").strip()
    if not text:
        return []
    # gh --paginate concatenates JSON arrays / objects as separate documents
    items: list[Any] = []
    decoder = json.JSONDecoder()
    idx = 0
    length = len(text)
    while idx < length:
        while idx < length and text[idx].isspace():
            idx += 1
        if idx >= length:
            break
        obj, end = decoder.raw_decode(text, idx)
        if isinstance(obj, list):
            items.extend(obj)
        else:
            items.append(obj)
        idx = end
    return items


def auth_status() -> AuthStatus:
    if not gh_available():
        return AuthStatus(
            logged_in=False,
            host="github.com",
            username=None,
            protocol=None,
            scopes=[],
            message="GitHub CLI (`gh`) is not installed.",
        )
    result = run_gh(["auth", "status"], check=False)
    combined = f"{result.stdout}\n{result.stderr}".strip()
    if result.returncode != 0:
        return AuthStatus(
            logged_in=False,
            host="github.com",
            username=None,
            protocol=None,
            scopes=[],
            message=combined or "Not logged in. Run: gh auth login",
        )

    username = None
    protocol = None
    host = "github.com"
    scopes: list[str] = []
    for line in combined.splitlines():
        stripped = line.strip()
        if "Logged in to" in stripped and "account" in stripped:
            # Logged in to github.com account USER (keyring)
            parts = stripped.split()
            if "account" in parts:
                idx = parts.index("account")
                if idx + 1 < len(parts):
                    username = parts[idx + 1]
            if "Logged in to" in stripped:
                try:
                    host = parts[parts.index("to") + 1]
                except (ValueError, IndexError):
                    pass
        if "Git operations protocol:" in stripped:
            protocol = stripped.split(":", 1)[1].strip()
        if "Token scopes:" in stripped:
            raw = stripped.split(":", 1)[1].strip()
            scopes = [s.strip().strip("'\"") for s in raw.split(",") if s.strip()]

    return AuthStatus(
        logged_in=True,
        host=host,
        username=username,
        protocol=protocol,
        scopes=scopes,
        message=combined,
    )


def current_username() -> str:
    status = auth_status()
    if status.logged_in and status.username:
        return status.username
    data = run_gh_json(["api", "user", "--jq", "{login:.login}"])
    if isinstance(data, dict) and data.get("login"):
        return str(data["login"])
    raise GhError("Unable to determine authenticated GitHub username", command=["gh", "api", "user"])
