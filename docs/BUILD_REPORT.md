# Jarvis build status

## Current state

- **Project home:** `D:\Jarvis`
- **Core:** partial custom Python text orchestrator
- **Model routing:** OpenRouter free-model route configured, with local Ollama fallback
- **Hermes Agent harness:** not installed or integrated; the current Python adapter is not Hermes Agent
- **Claude Code:** subprocess adapter exists; permission behavior and account usage need review
- **Memory:** local SQLite store; Honcho is not integrated
- **Skills:** scaffolding only
- **Browser and external accounts:** not connected
- **Autonomous tool loop:** not implemented
- **Security:** not verified; permission configuration exists, but enforcement and confirmation gates need review

## Brain setup still required

1. Complete the project setup with `D:\Jarvis\scripts\setup.ps1`.
2. Create an OpenRouter API key and save it to the ignored `D:\Jarvis\.env` file, following `D:\Jarvis\docs\BRAIN_SETUP.md`.
3. Make sure Ollama is installed and download the configured fallback model.
4. Configure Hermes Agent and a real tool loop as separate follow-up work before treating Jarvis as autonomous.
