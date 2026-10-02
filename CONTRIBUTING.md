# Contributing

## Development setup

```bash
git clone https://github.com/aprameyak/github-agent-skills.git
cd github-agent-skills
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
github-agent --version
ruff check .
pytest
```

Or use `./install.sh`, which creates `.venv` and links `github-agent` into `~/.local/bin`.

## Project layout

- `github_agent/` — deterministic collectors, analyzers, actions, CLI
- `skills/` — portable `SKILL.md` packages for coding agents
- `schemas/` — JSON schemas for snapshots and findings
- `tests/fixtures/` — multi-persona account snapshots
- `docs/` — architecture, safety, skill contract

## Contribution ideas

- New analyzers with clear evidence
- Clearer beginner-facing copy
- Additional fixtures / edge cases
- New skills that reuse collectors/analyzers (see `docs/contributing-skills.md`)

## Rules

1. Prefer deterministic checks over prompts for objective facts.
2. Every finding needs evidence.
3. No repository deletion, force-push, or silent archival.
4. Do not commit personal snapshots or tokens.
5. Keep dependencies minimal (stdlib by default).
6. Add tests for analyzer and CLI changes.

## Pull requests

- Keep PRs focused
- Include tests when behavior changes
- Update docs when user-facing behavior changes
