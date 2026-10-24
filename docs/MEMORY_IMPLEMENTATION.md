# Memory slice — 24 October 2026

Changed: core/memory/honcho_client.py, apps/jarvis/server.py,
ui/index.html, ui/components/app.js, ui/styles/app.css, README.md,
and tests/test_memory.py.

SQLite migration adds source and updated_at columns in place. No existing rows
are removed. New and edited facts are explicitly user-authored; legacy facts
retain their unknown provenance. Fact content is no longer written to logs.

The UI supports create/edit/delete, local filtering, metadata, and per-request
consent for bounded lexical retrieval. API mutations validate content, enforce
same-origin JSON, and return 404 for missing IDs. Tests cover legacy migration,
reopening persistence, validation, retrieval limits, CRUD, origin rejection, and
mocked Hermes submission with and without memory consent.

Limitations: no embeddings, export/undo, automatic extraction, secret detector,
or synchronization with Hermes memory. Deletion cannot retract facts from
previous sessions or providers. Screen context and workflow dashboards are
subsequent slices. Existing working-tree changes were preserved.
