# Jarvis acceptance checklist

**Checked:** 2026-10-24
**Result:** Not yet ready for end-to-end acceptance. Automated and local artifact checks pass; the live tool-execution check fails, and several account integrations still need setup.

## Verified

- Python test suite: 21 tests passed.
- Python source compilation, startup PowerShell syntax, and `git diff --check` passed.
- A generated sample PDF was parsed locally by the resume extraction helper.
- A sample job listing was exported to a valid XLSX workbook with a link and inline text.
- Jarvis and Hermes local health endpoints responded. Hermes reported its model and configured `web`, `browser`, `terminal`, `file`, `computer_use`, and `delegation` toolsets.
- Jarvis homepage and visualizer endpoints returned HTTP 200. Visualizer source includes idle, listening, thinking, and speaking states.
- Local profile and job-search skill files are present.
- Tracked-file scan found no API-key patterns.

## Failed or pending

| Capability | Status | Evidence / next step |
|---|---|---|
| Terminal, browser, and PC actions | Failed live check | Harmless terminal probe returned command-like text but no successful Hermes tool-completion event. Restart Jarvis and Hermes, then repeat the probe and require event evidence. |
| Council and independent agents | Unverified | Delegation toolset is configured, but the live run produced no delegate completion event. Council currently exists as an instruction protocol; verify an actual multi-agent run after restart. |
| Gmail, Calendar, Docs/Drive | Not connected | Google OAuth client and account token files are absent. Configure the Desktop OAuth client and complete account sign-in. |
| Claude Code as Jarvis's coding brain | Not ready | CLI is installed, but authentication is inactive and Jarvis chat does not route coding tasks through the Claude adapter. |
| Honcho long-term memory | Configured; live sync unverified | Honcho CLI authentication succeeds and the provider is selected in config, but Honcho reports no peer data yet. Restart the gateway and verify a test conversation sync. |
| Live job search and spreadsheet workflow | Partially verified | Local PDF parsing and XLSX export passed; live search and end-to-end matching remain unverified until tool execution works. |
| YouTube channel, phone, iMessage | Not connected / unavailable | YouTube channel authorization is pending. Native iMessage integration requires macOS Messages and is unavailable on this Windows host. No phone-service integration is configured. |
| OpenRouter model access | Not configured | Current brain uses local Qwen; no OpenRouter key is configured. |

## Acceptance gate

1. Restart Jarvis and Hermes so the running processes load the current code and configuration.
2. Repeat the harmless terminal probe and confirm a successful `tool.completed` event appears in run evidence.
3. Run one real delegated task and confirm subagent completion events and a bounded final report.
4. Run a live web search and verify results against destination pages; confirm the resulting XLSX downloads and opens.
5. Connect Google OAuth and verify read-only Gmail, Calendar, and Drive/Docs access before enabling any write actions.
6. Verify a non-sensitive conversation reaches Honcho after restart.
7. Authenticate Claude Code and test a coding task only after routing from Jarvis chat is implemented.

Do not treat configured toolsets, installed skills, model claims, or command-like text as proof of completed actions. Require runtime evidence for action capabilities. Keep API keys and OAuth credentials out of tracked files and GitHub.
