# github-agent-skills

Local skills + CLI so a coding agent can inspect and tidy a GitHub account using your existing `gh` auth. No hosted backend. No project-owned GitHub token. No OpenAI/Anthropic key required by this repo.

## Skills

| Skill | Purpose |
| --- | --- |
| `github-checkup` | Account and repo health summary |
| `github-cleanup` | Clutter candidates (review only) |
| `github-polish` | Profile/repo presentation fixes |
| `github-fix` | Small safe changes pending approval |
| `github-today` | What needs attention now |
| `github-recap` | Activity over a time range |

## Quick start

Needs: git, [GitHub CLI](https://cli.github.com/), Python 3.10+, and an agent that loads `SKILL.md` packs.

```bash
gh auth login
git clone https://github.com/aprameyak/github-agent-skills.git
cd github-agent-skills
./install.sh
```

Installer puts `github-agent` on your PATH (usually `~/.local/bin`) and symlinks skills into detected agent directories.

```bash
./install.sh --agents cursor,claude
./install.sh --agents all --copy
./install.sh --dry-run
export PATH="$HOME/.local/bin:$PATH"
```

CLI (no LLM required):

```bash
github-agent auth-check
github-agent checkup
github-agent today
github-agent recap --since 30d
github-agent fix --json
```

## How it works

```text
GitHub → gh CLI → local collectors/analyzers → skills → your coding agent
```

Deterministic code finds facts (missing descriptions, failed checks, stale repos). The agent handles wording and judgment.

More detail: [docs/architecture.md](docs/architecture.md).

## Safety

- Read-only by default
- Metadata: preview → approval → apply
- Content: branch → diff → approval → PR
- No repo deletion, force-push, or silent archival

[docs/safety.md](docs/safety.md)

## Agents

| Agent | Status |
| --- | --- |
| Claude Code | Verified (`~/.claude/skills`) |
| Cursor | Verified (`~/.cursor/skills`) |
| Codex CLI | Compatible per docs; confirm locally |
| Gemini CLI | Compatible per docs; confirm locally |

## Examples

```bash
github-agent today
github-agent cleanup
github-agent fix --json > findings.json
github-agent propose findings.json
github-agent apply-metadata --repo you/your-repo --description "Short accurate description"
github-agent apply-metadata --repo you/your-repo --description "Short accurate description" --execute
github-agent recap --since 7d
```

## Layout

```text
skills/         SKILL.md packs
github_agent/   collectors, analyzers, actions, CLI
schemas/        snapshot + findings
tests/fixtures/ mocked accounts
docs/           architecture, safety, skill contract
install.sh
```

## Contributing

[CONTRIBUTING.md](CONTRIBUTING.md) · [docs/contributing-skills.md](docs/contributing-skills.md)

## License

MIT
