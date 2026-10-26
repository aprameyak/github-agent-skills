# github-agent-skills

A local CLI (`github-agent`) and six agent skills for reviewing and tidying your GitHub account: missing READMEs, descriptions, and topics, stale or empty repos, what needs your attention today, and a recap of recent work. It uses your existing `gh` login, runs on your machine, and does not change anything on GitHub unless you approve a specific change.

## Example

Run against one of the test fixtures (output shortened):

```console
$ github-agent checkup --snapshot tests/fixtures/new_user.json
GitHub Checkup

I looked through your profile and 3 repositories.

I found 8 things worth looking at:

- 5 quick fixes
- 1 project that could be easier to understand

Most useful findings:

• “hello-world” is missing a README (hello-world)
  Without a README, visitors have to guess what the project does and how to get started.
  Evidence: has_readme=False, size=2
  Suggested next step: add readme
  Risk: medium · confidence: high

• Your GitHub profile is missing a few details
  Profiles with a name, short bio, and website are easier for people to understand. Missing: name, bio, website.
  Evidence: missing_fields=['name', 'bio', 'website']
  Suggested next step: complete profile
  Risk: low · confidence: high
...
```

Without `--snapshot`, the same command inspects your own account through `gh`.

## Features

- Every finding includes the evidence it is based on, a suggested next step, a risk level, and a confidence level. Heuristic findings are marked `[heuristic]`.
- `today`: review requests, open PRs, assigned issues, failed builds, dependency updates, and stale work.
- `recap --since 7d|30d|90d|year`: a summary of recent activity based on what the GitHub API returns.
- `cleanup`, `polish`, `fix`: conservative cleanup candidates, presentation improvements, and low-risk fix proposals.
- `propose` turns findings JSON into approval-required actions, and `apply-metadata` changes a repo's description, homepage, or topics. It is a dry run unless you pass `--execute`.
- Skills in `skills/` (`github-checkup`, `github-cleanup`, `github-polish`, `github-fix`, `github-today`, `github-recap`) let Cursor, Claude Code, Codex, or Gemini CLI run the same workflows from a chat.

The tool has no code path for deleting repositories, force-pushing, rewriting history, or changing visibility. See [docs/safety.md](docs/safety.md).

## Getting started

Prerequisites: Python 3.10+, git, and the [GitHub CLI](https://cli.github.com/) logged in with `gh auth login`. There are no third-party runtime dependencies.

```bash
git clone https://github.com/aprameyak/github-agent-skills.git
cd github-agent-skills
./install.sh
export PATH="$HOME/.local/bin:$PATH"   # if ~/.local/bin is not already on PATH
github-agent auth-check
github-agent checkup
```

`install.sh` creates `.venv`, installs the package in editable mode, links `github-agent` into `~/.local/bin`, and symlinks the skills into the skill folders of the agents it detects (`~/.cursor/skills`, `~/.claude/skills`, `~/.agents/skills` for Codex, `~/.gemini/skills`). Useful flags: `--agents cursor,claude` (or `all`), `--copy` instead of symlinks, `--cli-only`, `--skills-only`, and `--dry-run`.

## Usage

```bash
github-agent today
github-agent recap --since 30d
github-agent snapshot --out me.json             # save an account snapshot
github-agent findings --snapshot me.json --skill github-cleanup > findings.json
github-agent propose findings.json
github-agent apply-metadata --repo OWNER/NAME --description "..." --topics cli,python            # preview
github-agent apply-metadata --repo OWNER/NAME --description "..." --topics cli,python --execute  # apply
```

Most commands accept `--json` for machine-readable output and `--snapshot FILE` to work offline from a saved snapshot. Run `github-agent <command> --help` for all options.

## How it works

```text
gh -> collectors -> AccountSnapshot -> analyzers -> FindingsReport -> text/JSON report or skill -> optional approved gh mutation
```

- `github_agent/gh.py`: subprocess wrapper around `gh`. The project stores no tokens.
- `github_agent/collectors/`: builds the snapshot from `gh api` calls, plus README and latest workflow lookups for a bounded set of repos. It does not clone repositories.
- `github_agent/analyzers/`: deterministic checks that produce findings.
- `github_agent/actions/`: proposals and the metadata update used by `apply-metadata`.
- `github_agent/models/` and `schemas/`: the snapshot and findings data models and their JSON schemas.
- `skills/*/SKILL.md`: instructions that tell an agent which CLI commands to run and how to present the results.

More detail in [docs/architecture.md](docs/architecture.md) and [docs/skill-spec.md](docs/skill-spec.md).

## Contributing

Issues and pull requests are welcome; see [CONTRIBUTING.md](CONTRIBUTING.md) and [docs/contributing-skills.md](docs/contributing-skills.md). Before opening a PR, run:

```bash
pip install -e ".[dev]"
ruff check .
ruff format --check .
pytest
```

Security reports: see [SECURITY.md](SECURITY.md).

## License

MIT, see [LICENSE](LICENSE).
