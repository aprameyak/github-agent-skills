# Skill specification

Canonical skills live in `skills/<name>/SKILL.md` and follow the open Agent Skills convention:

```markdown
---
name: skill-name
description: What it does and when to use it
---

# Instructions
```

## Contract

Every skill should declare (in docs or the skill body):

| Field | Description |
| --- | --- |
| `name` | Lowercase hyphenated id |
| `description` | Trigger phrases + purpose |
| `required capabilities` | e.g. `auth`, `snapshot`, `analyze`, `recap` |
| `read/write` | `read_only` or mutation policy |
| `risk level` | max risk the skill may initiate |
| `evidence requirements` | findings must cite snapshot evidence |
| `failure behavior` | explain permission/partial failures honestly |

## Primary skills (v0.1)

- `github-checkup`
- `github-cleanup`
- `github-polish`
- `github-fix`
- `github-today`
- `github-recap`

## Agent install locations

| Agent | Skills directory |
| --- | --- |
| Claude Code | `~/.claude/skills/` |
| Cursor | `~/.cursor/skills/` |
| OpenAI Codex CLI | `~/.agents/skills/` |
| Gemini CLI | `~/.gemini/skills/` |

`./install.sh` can symlink or copy into these locations.
