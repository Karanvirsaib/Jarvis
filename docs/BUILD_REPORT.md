# Jarvis capability audit

Checked 24 October 2026 against the nine original Jarvis requirements.

## Verified in this build

- **Home:** project and live server run from `D:\Jarvis` on local loopback.
- **Harness:** Hermes Agent 0.22.5 is running at `127.0.0.1:8642`; Jarvis runs at `127.0.0.1:8765`.
- **Local brain:** Ollama has `qwen3.5:4b` available. OpenRouter has no configured key.
- **Memory foundation:** local SQLite facts and conversation history work. History is now scoped to the active Jarvis chat. `knowledge\USER_PROFILE.md` is attached only when the per-request memory checkbox is selected.
- **Skills:** Hermes exposes 56 skills through its API, including coding, research, browser research, Google Workspace, job search, resume optimization, data analysis, task automation, and YouTube content skills.
- **UI:** dashboard and fullscreen visualizer both load. The visualizer exposes idle/listening/thinking/speaking states and voice controls.
- **Automated checks:** 20 unittest cases pass; Python compilation and `node --check ui/components/app.js` pass.

## Failed or blocked

- **Tool execution and autonomous delegation: failed live acceptance.** The configured model returned a report claiming terminal and delegated work, but the Hermes run event stream contained only `message.delta` and `run.completed`; there were no tool or delegate events. Treat tool/action claims as unverified until a real model/tool-call test passes. This is the largest blocker to reliable autonomous work.
- **Claude Code brain: not integrated into Jarvis chat.** The CLI is installed, but `claude auth status` failed and the web request path does not call `ClaudeCodeAdapter`.
- **Honcho: not connected.** Plugin directory is installed, but `HONCHO_API_KEY` is absent and SQLite remains the active store.
- **Google services: blocked on OAuth setup.** Gmail, Calendar, and Docs/Drive skills exist, but no Google OAuth client file or token is configured.
- **Personal reference:** a local profile file exists and is now opt-in per request, but the content has not been independently confirmed as a complete profile. It is not sent by default.
- **Browser/PC access:** Hermes toolsets are configured and visible, but the acceptance run did not demonstrate tool execution. Browser login sessions and desktop control are not proven end to end.
- **YouTube channel:** the content skill is available; channel authentication is absent.
- **Phone/iMessage:** unavailable on this Windows host; the Hermes Messages skill requires macOS Messages.

## Changes made during this audit

- Added per-request profile-document inclusion alongside saved facts, with explicit UI consent.
- Scoped conversation context and assistant responses by Jarvis session to prevent a new chat receiving old-chat context.
- Added run-event evidence checks; action-shaped requests are marked unverified when no successful Hermes tool/delegate event exists.
- Added regression coverage for same-chat continuity and new-chat isolation.
- Changed dashboard wording so configured tools and agent delegation are not presented as live-verified actions.

External account sign-in and the tool-calling reliability blocker require further work. No emails, applications, uploads, or other external changes were performed during this audit.
