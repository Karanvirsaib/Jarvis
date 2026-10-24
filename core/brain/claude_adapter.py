import subprocess
import os
import json
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class ClaudeCodeAdapter:
    """
    Adapter to route heavy coding and analysis tasks to Claude Code CLI.
    """
    def __init__(self, allowed_dirs: list[str]):
        self.allowed_dirs = [Path(d).resolve() for d in allowed_dirs]

    def _is_safe_directory(self, target_dir: str) -> bool:
        target = Path(target_dir).resolve()
        return any(target.is_relative_to(allowed) for allowed in self.allowed_dirs)

    def execute_task(self, prompt: str, working_dir: str, timeout: int = 600) -> str:
        """
        Executes a prompt using Claude Code in non-interactive (print) mode.
        """
        if not self._is_safe_directory(working_dir):
            return f"Error: Directory {working_dir} is not in the allowed paths list in permissions.yaml."

        logger.info(f"Delegating task to Claude Code in {working_dir}...")

        # Build command: claude -p allows for a one-off headless prompt
        command = ["claude", "-p", prompt]

        try:
            result = subprocess.run(
                command,
                cwd=working_dir,
                capture_output=True,
                text=True,
                timeout=timeout,
                env=os.environ.copy() # Passes existing keys (like ANTHROPIC_API_KEY if present)
            )

            if result.returncode != 0:
                logger.error(f"Claude Code failed: {result.stderr}")
                return f"Claude Code execution failed:\n{result.stderr}"

            return result.stdout.strip()

        except subprocess.TimeoutExpired:
            logger.error("Claude Code task timed out.")
            return "Error: Claude Code execution timed out."
        except FileNotFoundError:
            logger.error("Claude Code CLI not found. Is it installed and in PATH?")
            return "Error: Claude CLI not installed or not found in system PATH."
