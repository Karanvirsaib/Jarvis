"""Small Windows launcher for the installed D:\\JARVIS runtime."""

from __future__ import annotations

import argparse
import ctypes
import os
from pathlib import Path
import shutil
import subprocess
import sys
from urllib.error import URLError
from urllib.request import urlopen


def _root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


def _message(title: str, body: str, *, error: bool = False) -> None:
    flags = 0x10 if error else 0x40
    try:
        ctypes.windll.user32.MessageBoxW(None, body, title, flags)
    except (AttributeError, OSError):
        print(f"{title}: {body}", file=sys.stderr if error else sys.stdout)


def _powershell() -> str:
    return shutil.which("powershell.exe") or str(
        Path(os.environ.get("WINDIR", r"C:\Windows"))
        / "System32" / "WindowsPowerShell" / "v1.0" / "powershell.exe"
    )


def _run_script(script_name: str) -> int:
    root = _root()
    script = root / "scripts" / script_name
    if not script.is_file():
        _message("Jarvis", f"Missing Jarvis script:\n{script}", error=True)
        return 2
    command = [
        _powershell(), "-NoProfile", "-ExecutionPolicy", "Bypass",
        "-File", str(script),
    ]
    try:
        result = subprocess.run(
            command,
            cwd=root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=150,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        _message("Jarvis could not start", str(exc), error=True)
        return 1
    if result.returncode:
        details = (result.stderr or result.stdout or "Startup script returned an error.").strip()
        _message("Jarvis could not start", details[-3000:], error=True)
    return result.returncode


def _check() -> int:
    root = _root()
    required = (
        root / "scripts" / "start_jarvis.ps1",
        root / "scripts" / "stop_jarvis.ps1",
        root / "venv" / "Scripts" / "python.exe",
        root / "hermes-home" / "bin" / "hermes.exe",
    )
    missing = [str(item) for item in required if not item.is_file()]
    if missing:
        _message("Jarvis check failed", "Missing required files:\n" + "\n".join(missing), error=True)
        return 2
    try:
        with urlopen("http://127.0.0.1:8765/api/status", timeout=2) as response:
            if response.status != 200:
                raise URLError(f"Jarvis returned HTTP {response.status}")
    except (OSError, URLError) as exc:
        _message("Jarvis check", f"Launcher files are present. Jarvis is not running yet.\n{exc}")
        return 1
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Start or stop the Jarvis desktop app.")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--stop", action="store_true", help="Stop Jarvis services")
    mode.add_argument("--check", action="store_true", help="Check launcher files and local server")
    args = parser.parse_args()
    if args.check:
        return _check()
    if args.stop:
        return _run_script("stop_jarvis.ps1")
    return _run_script("start_jarvis.ps1")


if __name__ == "__main__":
    raise SystemExit(main())
