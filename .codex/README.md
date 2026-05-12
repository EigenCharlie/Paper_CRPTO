# Codex Project Setup

Local Codex skills for CRPTO live under `.codex/skills/`. They are intended as
project-specific guardrails and runbooks for future agent sessions.

The skills do not contain secrets. They point agents to `.env.example` and
`docs/security/SECRETS_AND_REMOTES.md` for environment setup.

This repository is now Windows-native for day-to-day Codex work. Use
PowerShell, `uv`, `just`, DVC and Quarto directly from
`C:\Users\carlos\Documents\Paper_CRPTO`; do not route normal work through
non-Windows shells.
