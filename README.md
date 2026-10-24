# JARVIS

A personal assistant scaffold rooted at `D:\Jarvis`.

## Architecture
- **Orchestrator**: Custom Python routing engine
- **Executive Brain**: OpenRouter free-model route with local Ollama fallback
- **Coding Brain**: Claude Code (`claude -p`) using Anthropic APIs
- **Memory**: Local SQLite store

The web interface connects to the local Hermes gateway for agent runs and stop
controls. The older CLI orchestrator still uses a separate text-only model
adapter. See `docs/JARVIS_RUNTIME_SETUP.md` for runtime details.

## Saved memory

Open **Memory** to add, search, edit, and delete saved facts. Existing facts and
conversation history are preserved. Each fact has an ID, category, source
(`user` or `legacy`), creation time, and last-update time.

Enable **Include relevant saved facts** beside the chat composer to attach facts
to that request. The checkbox resets after submission. Retrieval selects up to
eight facts within a 4,000-character serialized budget using word overlap;
Profile and Preferences categories are eligible across requests. This is lexical
retrieval, not embedding search. Chat reports the number and categories used.
Facts may reach any configured model provider, including cloud fallback. Keep
credentials out of memory. Deleting a fact does not remove previous messages,
Hermes session context, or copies already sent to providers. Hermes maintains its
own memory separately; this page manages the Jarvis SQLite facts only.

Run `venv\Scripts\python.exe -m unittest discover -s tests -v` and
`node --check ui/components/app.js` to verify the memory slice. API tests use a
mock Hermes response; no model call or account connection is required.

## Chat recovery

Chat now uses a generated session ID stored in the local SQLite application state,
instead of the legacy hardcoded `jarvis-local-workspace` session. The session
survives web restarts. **New conversation** starts a fresh Hermes session without
deleting history or restarting earlier tasks. Use it when an earlier conversation
is blocked; existing unknown executions must be investigated separately before
any replay. Saved facts remain available through the per-request memory checkbox.

## Screen context

Open **Screen context**, capture a screen/window through the browser picker or
choose an image file, review the preview, and click **Analyze locally**.
The preview is resized to at most 1,600 pixels on its longest edge. Jarvis sends
only that image and question to local Ollama (`127.0.0.1:11435`, `qwen3.5:4b`).
There is no cloud fallback, screenshot persistence, tool execution, or continuous
capture. Capture tracks stop immediately after the frame is obtained. Browser
capture support varies; choosing a screenshot is the fallback. Clear removes the
preview and answer from the page. Vision requests have a 180-second timeout.

## Workflow dashboard

Open **Workflows** to save a title, objective, and up to 12 ordered steps, then
start it manually. Each execution gets an isolated Hermes session, so a paused
chat session cannot block a new workflow. Hermes executes the instructions in one run. The page tracks
run status, stop requests, and results; it does not claim individual steps were
independently verified. Refresh reconnects to existing run IDs without replaying
work. New chat runs also appear in history. Definitions and the latest 100 run
references/results persist in `data/jarvis_workflows.sqlite3`. Opening the page
refreshes up to ten active runs every five seconds; archived results remain
available after restart. Workflows are user-triggered, not scheduled. Hermes
controls tool permissions/approvals; this slice adds no independent approval
queue, task dependency engine, failed-step resume, or automatic retries.

## Getting Started

1. Stage permissions to the final drive location.
2. Run `.\scripts\setup.ps1` to configure Python.
3. Run `.\scripts\start_jarvis.ps1` to launch the local web interface.
4. Open `http://127.0.0.1:8765` if the browser does not open automatically.

The dashboard shows live model readiness and clearly labels integrations and agents
that are still planned. It listens only on the local computer.

## Skills & Integrations
*To be expanded per user configuration in `config/permissions.yaml`.*
