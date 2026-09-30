# Contributing

Thanks for helping make GitHub more approachable for every kind of builder.

## Development setup

```bash
git clone https://github.com/aprameyak/github-agent-skills.git
cd github-agent-skills
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
github-agent --version
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
- Better beginner-friendly copy
- Additional fixtures / edge cases
- Agent adapter improvements
- New skills that reuse the shared intelligence layer (see `docs/contributing-skills.md`)

## Rules of the road

1. Prefer deterministic checks over prompts for objective facts.
2. Every finding needs evidence.
3. No repository deletion, force-push, or silent archival.
4. Do not commit personal dogfood snapshots or tokens.
5. Keep dependencies minimal (stdlib by default).
6. Add tests for analyzer and CLI changes.

## Pull requests

- Keep PRs focused
- Include tests when behavior changes
- Update docs when user-facing behavior changes

## Code of conduct expectation

Be kind. This project is for students, hobbyists, designers, and professionals alike.
