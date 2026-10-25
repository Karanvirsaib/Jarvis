# Jarvis runtime setup and operating status

Jarvis UI and runtime live in `D:\Jarvis`. Start with `scripts\start_jarvis.ps1` and stop with `scripts\stop_jarvis.ps1`. Hermes runs its local API on `127.0.0.1:8642`; the Jarvis UI binds to `127.0.0.1:8765`. Runtime config and keys stay in the ignored `hermes-home` folder.

## Model setup

The primary route is local Qwen 3.5 4B over Ollama at `http://127.0.0.1:11435/v1`, stored in `D:\Jarvis\data\models\ollama`. Jarvis starts this loopback-only endpoint. Hermes has an OpenRouter `openrouter/free` fallback, which requires a valid OpenRouter API key in `hermes-home\.env`; no key is configured yet.

## Agents and work limits

Hermes is configured for up to three concurrent child agents, flat delegation, 30 tool turns per run/child, and Jarvis instructs one materially different recovery attempt before reporting a blocker. The council is a structured planning/challenge/review protocol. Hermes may delegate independent work, but specialist role choice and completion depend on task context and actual returned agent outputs.

## Coding and memory

Claude Code is installed on PATH, but the CLI is not authenticated and Jarvis's web chat does not route coding requests through the existing `ClaudeCodeAdapter`. The current chat brain is local Qwen through Hermes.

Jarvis stores UI conversation history and saved facts in local SQLite. The file `knowledge\USER_PROFILE.md` is attached only when **Include saved facts and your local profile** is checked; this shares it with the configured model for that request. Chat history is scoped to the active conversation. Honcho is selected as Hermes's persistent memory provider, and its API key is stored in the ignored local `hermes-home\.env`. The Honcho CLI authenticated successfully. The existing Hermes gateway started before this key and provider configuration were added, so restart Jarvis/Hermes for active chat sessions to use Honcho. Context recall is enabled; automatic dialectic reasoning is deferred to avoid unexpected metered calls. Built-in SQLite conversation history remains local.

## Still awaiting account/device setup

Gmail, Google Calendar, Docs/Drive, YouTube channel access, phone/iMessage, and authenticated browser profiles are not connected. Google OAuth needs a downloaded Desktop app client at `hermes-home\google_client_secret.json` and user sign-in. YouTube channel access needs its own authorization. The Hermes Messages skill requires macOS Messages and cannot run on this Windows host. Browser, file, terminal, and desktop toolsets appear configured, but a live run produced no tool-call events even though the model claimed it used tools. Treat those actions as unverified until a tool-capable model passes an event-checked acceptance test. Do not send emails, apply to jobs, submit forms, publish, make purchases, or delete personal data without explicit user approval.
