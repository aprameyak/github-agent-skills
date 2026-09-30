# github-agent-skills

**Give your coding agent GitHub superpowers.**

Open-source, local-first skills that help any compatible CLI coding agent understand and take care of your **entire GitHub account** — whether you have 3 repos or 300.

No hosted backend. No extra GitHub token for us. No OpenAI/Anthropic key required by this project. It uses the `gh` session already on your machine.

## What you can ask

After install, ask your coding agent things like:

- “Check my GitHub.”
- “Clean up my GitHub.”
- “Make my GitHub look better.”
- “Fix the easy stuff.”
- “What needs my attention on GitHub?”
- “What have I done on GitHub this month?”

## Skills

| Skill | Purpose |
| --- | --- |
| `github-checkup` | How’s my GitHub doing? |
| `github-cleanup` | What clutter should I review? |
| `github-polish` | Make my profile/repos look put together |
| `github-fix` | Safe, small improvements pending approval |
| `github-today` | What needs attention right now? |
| `github-recap` | What did I actually do over a time period? |

## Who it’s for

Students, hobby programmers, designers who code, hackathon teams, new developers, professionals, and maintainers.

The default voice is approachable. Technical detail is available when useful — without assuming you already know CI, GraphQL, or “repository hygiene scores.”

## Quick start

### Prerequisites

1. [git](https://git-scm.com/)
2. [GitHub CLI](https://cli.github.com/) (`gh`)
3. Python 3.10+
4. A coding agent that supports Agent Skills (`SKILL.md`) — see compatibility below

```bash
gh auth login
```

### Install

```bash
git clone https://github.com/aprameyak/github-agent-skills.git
cd github-agent-skills
./install.sh
```

The installer:

- installs the `github-agent` CLI (user-level pip)
- detects compatible agents when possible
- symlinks the six portable skills into agent skill directories

Useful variants:

```bash
./install.sh --agents cursor,claude
./install.sh --agents all --copy
./install.sh --dry-run
```

Make sure `~/.local/bin` is on your `PATH` (the installer links `github-agent` there):

```bash
export PATH="$HOME/.local/bin:$PATH"
```

### Try the deterministic CLI (no LLM required)

```bash
github-agent auth-check
github-agent checkup
github-agent today
github-agent recap --since 30d
github-agent fix --json
```

Example:

```text
$ github-agent checkup

GitHub Checkup

I looked through your profile and 12 repositories.

I found 7 things worth looking at:

- 3 quick fixes
- 2 projects that could be easier to understand
- 1 older project worth reviewing
- 1 failed automated build
```

## How it works

```text
Your GitHub
  → authenticated GitHub CLI (`gh`)
  → deterministic local intelligence layer
  → portable agent skills
  → whatever CLI coding agent you prefer
```

Deterministic code finds objective facts (missing descriptions, failed builds, stale repos, review requests…). Your coding agent handles semantic work (writing an accurate description, improving README prose, explaining findings clearly).

See [docs/architecture.md](docs/architecture.md).

## Safety

- Read-only by default
- Metadata changes: preview → approval → apply
- Content changes: branch → diff → approval → PR
- **No repository deletion**
- **No force-push / history rewrite**
- **No silent archival**

Details: [docs/safety.md](docs/safety.md).

## Privacy

- Runs locally
- Uses your existing `gh` auth
- Does not send your token to this project’s servers (there are none)
- Does not require an account with us
- No telemetry in v0.1

## Supported agents

| Agent | Status | Skills path |
| --- | --- | --- |
| **Claude Code** | Verified (`SKILL.md` in `~/.claude/skills`) | portable skills install |
| **Cursor** | Verified (`SKILL.md` in `~/.cursor/skills`) | portable skills install |
| **OpenAI Codex CLI** | Compatible per current docs (`~/.agents/skills`); not installed in the release dogfood environment | experimental until you confirm locally |
| **Gemini CLI** | Compatible per current docs (`~/.gemini/skills` / `.agents/skills`); not installed in the release dogfood environment | experimental until you confirm locally |

We don’t claim compatibility we haven’t checked. See [docs/skill-spec.md](docs/skill-spec.md).

## Examples

```bash
# Account briefing
github-agent today

# Cleanup candidates (review only — never deletes)
github-agent cleanup

# Low-risk fix proposals as JSON
github-agent fix --json > findings.json
github-agent propose findings.json

# Dry-run a metadata change
github-agent apply-metadata --repo you/your-repo --description "Short accurate description"

# Apply only after you approve
github-agent apply-metadata --repo you/your-repo --description "Short accurate description" --execute

# Activity recap
github-agent recap --since 7d
github-agent recap --since year --json
```

## Project layout

```text
skills/                # portable SKILL.md packages
github_agent/          # collectors, analyzers, actions, CLI
schemas/               # snapshot + findings schemas
tests/fixtures/        # multi-persona mocked accounts
docs/                  # architecture, safety, skill contract
install.sh             # CLI + skill installer
```

## Contributing

PRs welcome — especially analyzers, fixtures, beginner-friendly copy, and new skills that reuse the shared layer.

- [CONTRIBUTING.md](CONTRIBUTING.md)
- [docs/contributing-skills.md](docs/contributing-skills.md)

## Roadmap

- Richer Level-3 shallow-clone polish workflows
- Optional homepage link checking by default with clearer timeouts
- More skills: Actions, security alerts, docs, releases, org views
- Deeper pagination controls for very large accounts
- Packaged releases on PyPI

## License

MIT — see [LICENSE](LICENSE).
