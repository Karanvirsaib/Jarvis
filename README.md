# JARVIS

A personal assistant scaffold rooted at `D:\Jarvis`.

## Architecture
- **Agent harness**: Hermes Agent
- **Current brain**: local Qwen 3.5 4B through Ollama; OpenRouter is not configured
- **Claude Code**: CLI and adapter are present, but chat routing and CLI authentication are not set up
- **Memory**: local SQLite; Honcho plugin is installed but disconnected

The web interface connects to the local Hermes gateway for agent runs and stop
controls. Hermes delegation and toolsets are configured, but a live acceptance
run failed to produce tool-call events. Do not treat generated action reports as
verified until tool execution passes. See `docs/JARVIS_RUNTIME_SETUP.md` for
runtime details.

## Saved memory

Open **Memory** to add, search, edit, and delete saved facts. Existing facts and
conversation history are preserved. Each fact has an ID, category, source
(`user` or `legacy`), creation time, and last-update time.

Enable **Include saved facts and your local profile** beside the chat composer
to attach up to eight relevant facts, plus `knowledge/USER_PROFILE.md`, to that
request. The checkbox resets after submission and makes sharing with the
configured model explicit. Fact retrieval is lexical, not embedding search.
Keep credentials out of memory. Deleting a fact does not remove previous
messages, Hermes session context, or copies already sent to providers. Hermes
maintains its own memory separately; this page manages the Jarvis SQLite facts.

Run `venv\Scripts\python.exe -m unittest discover -s tests -v` and
`node --check ui/components/app.js` to verify the memory slice. API tests use a
mock Hermes response; no model call or account connection is required.

## Chat recovery

Chat now uses a generated session ID stored in the local SQLite application state,
instead of the legacy hardcoded `jarvis-local-workspace` session. The session
survives web restarts. **New conversation** starts a fresh Hermes session without
deleting history or restarting earlier tasks. Use it when an earlier conversation
is blocked; existing unknown executions must be investigated separately before
any replay. Jarvis supplies a bounded slice of the active chat's local history to
help resolve follow-ups. History is tagged by session so **New conversation**
cannot include messages from the prior chat. Legacy untagged messages are
assigned to the active chat on first use after migration. Saved facts and the
profile document remain available through the per-request memory checkbox.

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

## Job research and Excel exports

Ask Jarvis to find roles and provide the target title, location/work mode, years
of experience, and skills (or attach a resume with **＋ Files**). When Hermes'
web toolset is enabled, Jarvis uses web search for discovery and checks public
destination pages before marking a listing active. Search snippets alone are
not proof that a job is still open. Each result should include direct source
links, retrieval time, match reasons, gaps, and any source coverage limits.
Selected PDF resumes are extracted locally with pypdf before matching; Jarvis
must not guess candidate details from the filename or a generic profile. Scanned
or encrypted PDFs are reported as unreadable until an OCR-ready or text copy is
available.
Verified listings are returned in a local `.xlsx` workbook with a download link
in the chat. The file is saved under `data/exports`; the download endpoint is
loopback-only. Jarvis does not apply or contact employers without your approval.

## Getting Started

1. Stage permissions to the final drive location.
2. Run `.\scripts\setup.ps1` to configure Python.
3. Run `jarvis` from PowerShell or CMD to start Jarvis in its standalone app window.
   You can also run `scripts/start_jarvis.ps1` from this folder, or double-click `Jarvis.exe` in `D:\Jarvis`.
   `Jarvis.exe` is a launcher for the installed `D:\Jarvis` runtime; it expects the local Python environment and Hermes installation to be present. Use `Jarvis.exe --stop` to stop Jarvis services.
4. If the app window does not open, visit `http://127.0.0.1:8765` in a browser.

The dashboard shows live model readiness and clearly labels integrations and agents
that are still planned. It listens only on the local computer.

## Skills & Integrations
*To be expanded per user configuration in `config/permissions.yaml`.*

## Job Application Workflow

The `job-application-assistant` Hermes skill adapts the MIT-licensed [ai-job-search](https://github.com/MadsLorentzen/ai-job-search) application workflow for Jarvis. It covers evidence-based job fit evaluation, truthful resume and cover-letter drafts, independent read-only review when delegation is available, interview preparation, and optional local tracking. Job discovery, destination verification, local PDF parsing, and XLSX exports remain in the existing `job-search` workflow. Drafts belong under `data/career/applications`; source resumes are preserved. Jarvis stops for specific approval before submitting applications or transmitting personal data. The upstream's Claude-only commands and Denmark-specific portal CLIs are not installed.
