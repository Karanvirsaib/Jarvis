# Chat recovery — 24 October 2026

Cause: /api/runs used the hardcoded jarvis-local-workspace session for every chat.
Hermes logged unknown_execution and paused that session after a previous interrupted
execution. New submissions returned admission responses but could not execute.
Workflow sessions were already isolated and could complete normally.

Fix: generated jarvis-chat session selection persists transactionally in SQLite.
The legacy session and conversation history remain intact. A New conversation
control rotates the selected session without replaying old work. The control is
disabled while a run is active. Provider admission errors no longer log response
bodies, avoiding accidental disclosure of private content.

Tests verify session persistence, rotation, history preservation, and request
routing. Full unittest discovery passes 14 tests; JavaScript syntax check passes.
Live chat verification uses a harmless no-tool reply request in the actual UI.
