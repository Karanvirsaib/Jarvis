# Jarvis runtime setup and operating status

Jarvis UI and runtime live in `D:\Jarvis`. Start with `scripts\start_jarvis.ps1` and stop with `scripts\stop_jarvis.ps1`. Hermes runs its local API on `127.0.0.1:8642`; the Jarvis UI binds to `127.0.0.1:8765`. Runtime config and keys stay in the ignored `hermes-home` folder.

## Model setup

The primary route is local Qwen 3.5 4B over Ollama at `http://127.0.0.1:11435/v1`, stored in `D:\Jarvis\data\models\ollama`. Jarvis starts this loopback-only endpoint. Hermes has an OpenRouter `openrouter/free` fallback, which requires a valid OpenRouter API key in `hermes-home\.env`; no key is configured yet.

## Agents and work limits

Hermes is configured for up to three concurrent child agents, flat delegation, 30 tool turns per run/child, and Jarvis instructs one materially different recovery attempt before reporting a blocker. The council is a structured planning/challenge/review protocol. Hermes may delegate independent work, but specialist role choice and completion depend on task context and actual returned agent outputs.

## Coding and memory

Claude Code is installed on PATH and can be used as a coding specialist if its CLI login is valid. It is not the model that runs every Jarvis conversation.

Jarvis currently stores UI conversation history and facts in local SQLite. `knowledge\USER_PROFILE_TEMPLATE.md` is a blank template; populate it with confirmed details when ready, then rename it to `USER_PROFILE.md`. The Honcho plugin is installed but inactive. It sends conversation turns and derived memories to the Honcho service once configured; add HONCHO_API_KEY and explicitly set memory.provider to honcho only when ready. Do not label Honcho connected until authenticated and active. Hermes first-run setup or plugin catalog actions may require network access and explicit account login.

## Still awaiting account/device setup

Gmail, Google Calendar, Docs/Drive, YouTube, phone/iMessage, and authenticated browser profiles are not connected. Do not send emails, apply to jobs, submit forms, publish, make purchases, or delete personal data without explicit user approval. Windows desktop-control driver registration can require administrator/UAC setup; it is not enabled by this launcher.
