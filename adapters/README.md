# Agent adapters

Canonical skills live in `/skills`.

`./install.sh` places them into agent-specific directories:

| Agent | Destination |
| --- | --- |
| Cursor | `~/.cursor/skills/<skill>/` |
| Claude Code | `~/.claude/skills/<skill>/` |
| Codex CLI | `~/.agents/skills/<skill>/` |
| Gemini CLI | `~/.gemini/skills/<skill>/` |

Default mode is symlink so updates in this repo are picked up immediately.
Use `--copy` for a snapshot install.
