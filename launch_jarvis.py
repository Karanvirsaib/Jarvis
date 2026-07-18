"""Double-click launcher for the Jarvis desktop application."""

from pathlib import Path
import subprocess
from tkinter import messagebox


PROJECT_DIRECTORY = Path(r"C:\Users\karan\Downloads\Documents\New folder\Jarvis\Jarvis")
PYTHONW = PROJECT_DIRECTORY / "venv" / "Scripts" / "pythonw.exe"
ENTRY_POINT = PROJECT_DIRECTORY / "main.py"


def main() -> None:
    if not PYTHONW.is_file() or not ENTRY_POINT.is_file():
        messagebox.showerror(
            "Jarvis launcher",
            "Jarvis or its Python environment could not be found.\n\n"
            f"Expected project: {PROJECT_DIRECTORY}",
        )
        return

    try:
        subprocess.Popen(
            [str(PYTHONW), str(ENTRY_POINT), "--mode", "desktop"],
            cwd=PROJECT_DIRECTORY,
        )
    except OSError as exc:
        messagebox.showerror("Jarvis launcher", f"Jarvis could not start:\n{exc}")


if __name__ == "__main__":
    main()
