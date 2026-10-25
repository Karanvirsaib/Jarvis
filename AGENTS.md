# Jarvis repository instructions

- Preserve user's existing local edits, secrets, and runtime data.
- After changing Jarvis features, run relevant checks, then rebuild `Jarvis.exe` with `scripts/build_jarvis.ps1`.
- `Jarvis.exe` is a launcher. It starts the Python, Hermes, and UI files from the adjacent Jarvis folder; it is not a self-contained deployment.
- Never include `.env`, API keys, OAuth tokens, credentials, or private user data in the executable or source control.
