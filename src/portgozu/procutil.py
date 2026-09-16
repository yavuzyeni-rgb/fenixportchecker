"""Subprocess helpers that never flash a console window on Windows."""

from __future__ import annotations

import subprocess
import sys
from typing import Any


def windows_hidden_kwargs() -> dict[str, Any]:
    """Flags so child processes do not allocate a visible console on Windows."""
    if sys.platform != "win32":
        return {}
    # 0x08000000 == CREATE_NO_WINDOW (Python 3.7+ exposes the name)
    flags = int(getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000))
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    # 0 == SW_HIDE; belt-and-suspenders with CREATE_NO_WINDOW
    startupinfo.wShowWindow = 0
    return {
        "creationflags": flags,
        "startupinfo": startupinfo,
    }


def run_hidden(args: list[str], **kwargs: Any) -> subprocess.CompletedProcess[Any]:
    """subprocess.run with Windows console suppression applied."""
    merged = dict(kwargs)
    win = windows_hidden_kwargs()
    if win:
        existing = int(merged.get("creationflags", 0) or 0)
        merged["creationflags"] = existing | int(win["creationflags"])
        merged.setdefault("startupinfo", win["startupinfo"])
    return subprocess.run(args, **merged)


def powershell_hidden(script: str, *, timeout: float) -> subprocess.CompletedProcess[Any]:
    """Run a PowerShell script without showing a window."""
    return run_hidden(
        [
            "powershell",
            "-NoProfile",
            "-NonInteractive",
            "-WindowStyle",
            "Hidden",
            "-Command",
            script,
        ],
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
