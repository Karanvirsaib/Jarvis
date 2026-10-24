# Screen context and workflow dashboard — 24 October 2026

Changed: core/screen_context.py, core/workflows.py, core/memory/honcho_client.py,
apps/jarvis/server.py, ui/index.html, ui/components/app.js,
ui/components/features.js, ui/styles/app.css, tests/test_memory.py,
tests/test_features.py, README.md.

No dependency or model installation. Local Ollama reports vision capability for
qwen3.5:4b. Screen preview comes from explicit browser capture or file selection;
user analysis submission sends it only to the fixed loopback model endpoint.
Requests enforce PNG/base64/dimension/size limits and single concurrent vision
analysis. No server-side capture, permanent screenshot storage, or cloud fallback.

Workflows reuse /v1/runs and /v1/runs/{id}[/stop]. SQLite stores user definitions
and execution references. A terminal result is appended once to conversation
history transactionally, surviving repeated polling and restart. The workflow
page reconnects by run ID and never starts a run automatically after refresh.
Run state belongs to Hermes; ordered steps are instructions, not a durable DAG.

Automated checks: unittest discovery (temporary databases, mocked model/Hermes),
node --check for both UI scripts, and git diff --check. Manual verification uses
a synthetic red PNG and a no-tool arithmetic workflow; no personal screenshots
or external account operations are used.

Limitations: no cropping, continuous screen sharing, workflow scheduling,
step-level checkpoints/resume, or independent approvals. Browser capture picker
requires user interaction; image-file preview is tested separately.

Live checks: local Qwen identified the synthetic PNG as red. The first workflow
was blocked by a pre-existing unknown_execution pause in the shared chat session;
it was stopped through the dashboard. New workflow executions now use unique
sessions, preserving the paused session and its history. The replacement run
progressed to running. Native screen-picker interaction remains user-driven.

Final verification: isolated workflow completed with "4. Workflow ready"; the
result expanded in the UI. Dashboard stop was confirmed as cancelled on the
blocked test run. Local vision preview and red-color answer were verified in the
UI. Screenshots: docs/screenshots/screen-context.jpg and workflows.jpg.

Commands and outcomes:
- venv\Scripts\python.exe -m unittest discover -s tests -q: 11 tests passed.
- node --check ui/components/features.js: passed.
- node --check ui/components/app.js: passed.
- git diff --check: passed (existing CRLF conversion warnings only).

The original shared chat session remains paused in Hermes; no unknown prior
execution was reset or replayed. This pre-existing issue does not affect the new
isolated workflow sessions or the direct local vision route.
