from pathlib import Path


README_CONTENT = r"""# JARVIS

A personal assistant scaffold rooted at `D:\\Jarvis`.

## Architecture
- **Orchestrator**: Custom Python routing engine
- **Executive Brain**: OpenRouter free-model route with local Ollama fallback
- **Coding Brain**: Claude Code CLI adapter (account and permission behavior needs review)
- **Memory**: Local SQLite store

The current executive adapter returns text only. It is not the Hermes Agent
harness and does not yet provide autonomous tool calling. See
[`docs/BRAIN_SETUP.md`](docs/BRAIN_SETUP.md) for model setup and limitations.

## Getting Started

1. Run `.\scripts\setup.ps1` to configure Python.
2. Run `.\scripts\start_jarvis.ps1` to begin conversation.

## Skills & Integrations
*To be expanded per user configuration in `config/permissions.yaml`.*
"""

root = Path(__file__).resolve().parent.parent
with (root / "README.md").open("w", encoding="utf-8") as readme:
    readme.write(README_CONTENT)
