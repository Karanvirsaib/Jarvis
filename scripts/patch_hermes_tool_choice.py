"""Apply Jarvis's action-tool enforcement to the installed Hermes runtime.

Hermes is installed outside the tracked repository. This idempotent, version-guarded
patch keeps the local runtime change reproducible without vendoring its source.
"""
from __future__ import annotations

from pathlib import Path
import sys


def replace_once(path: Path, old: str, new: str) -> None:
    source = path.read_text(encoding="utf-8")
    if new in source:
        return
    if old not in source:
        raise RuntimeError(f"Unsupported Hermes source layout in {path}")
    path.write_text(source.replace(old, new, 1), encoding="utf-8")


def patch(root: Path) -> None:
    gateway = root / "gateway" / "platforms" / "api_server.py"
    helper = root / "agent" / "chat_completion_helpers.py"
    executor = root / "agent" / "tool_executor.py"
    if not all(path.is_file() for path in (gateway, helper, executor)):
        return

    replace_once(
        gateway,
        "        agent = AIAgent(**agent_kwargs)\n",
        "        agent = AIAgent(**agent_kwargs)\n"
        "        # Jarvis action requests require one native Hermes tool call before a text reply.\n"
        "        agent._jarvis_tool_call_pending = bool(\n"
        "            isinstance(model_options, dict) and model_options.get('jarvis_require_tool_call') is True\n"
        "        )\n",
    )
    replace_once(
        helper,
        "    request_overrides = effective_request_overrides(agent)\n",
        "    request_overrides = effective_request_overrides(agent)\n"
        "    if getattr(agent, '_jarvis_tool_call_pending', False):\n"
        "        request_overrides['tool_choice'] = 'required'\n",
    )
    replace_once(
        executor,
        "    tool_calls = assistant_message.tool_calls\n    num_tools = len(tool_calls)\n",
        "    tool_calls = assistant_message.tool_calls\n"
        "    if tool_calls:\n        agent._jarvis_tool_call_pending = False\n"
        "    num_tools = len(tool_calls)\n",
    )
    replace_once(
        executor,
        "    tool_calls = assistant_message.tool_calls\n\n    for i, tool_call in enumerate(tool_calls, 1):\n",
        "    tool_calls = assistant_message.tool_calls\n"
        "    if tool_calls:\n        agent._jarvis_tool_call_pending = False\n\n"
        "    for i, tool_call in enumerate(tool_calls, 1):\n",
    )


def main() -> int:
    repo = Path(__file__).resolve().parents[1]
    roots = [repo / "vendor" / "hermes-agent"]
    home = Path(__import__("os").environ.get("HERMES_HOME", repo / "hermes-home"))
    roots.extend(home.glob("installs/*/environments/*/workspace"))
    roots.extend(home.glob("installs/*/environments/*/Lib/site-packages"))
    roots.extend(home.glob("installs/*/environments/*/venv/Lib/site-packages"))
    roots.extend(home.glob("installs/*/environments/*/lib/python*/site-packages"))
    roots.extend(home.glob("*/Lib/site-packages"))
    seen: set[Path] = set()
    patched = 0
    for root in roots:
        try:
            resolved = root.resolve()
        except OSError:
            continue
        if resolved in seen or not (resolved / "gateway" / "platforms" / "api_server.py").is_file():
            continue
        seen.add(resolved)
        patch(resolved)
        patched += 1
    if not patched:
        print("Could not find Hermes source files to patch.", file=sys.stderr)
        return 1
    print(f"Jarvis tool-call enforcement ready ({patched} Hermes source tree(s)).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
