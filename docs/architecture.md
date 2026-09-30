# Architecture

## Pipeline

```text
GitHub
  → authenticated `gh`
  → collectors (progressive inspection)
  → AccountSnapshot (normalized)
  → deterministic analyzers
  → FindingsReport
  → portable SKILL.md agents + human/JSON reporting
  → optional approved actions (`gh` mutations)
```

## Layers

### `github_agent/gh.py`

Subprocess wrapper around the GitHub CLI. No tokens are stored by this project.

### Collectors

Build an `AccountSnapshot`:

- Level 1: API metadata via `gh api` (profile, repos, search for attention items, events)
- Level 2: lightweight README / latest workflow lookups for a bounded subset
- Level 3: shallow clone is reserved for future content-edit workflows (not used for checkup)

Collectors never blindly clone hundreds of repositories.

### Analyzers

Pure functions over snapshots. They emit `Finding` objects with evidence, confidence, risk, and recommended actions.

Heuristic findings are marked `heuristic: true`.

### Actions

Proposal + dry-run + explicit `--execute` for low-risk metadata.

Content edits are intentionally agent-orchestrated (branch → diff → approval → PR).

### Skills

Portable Agent Skills (`skills/*/SKILL.md`) teach any compatible CLI agent how to call the CLI and talk to humans. Core logic is not duplicated per agent.

## Extensibility

New skills should usually:

1. Reuse collectors / snapshot
2. Add or filter analyzers
3. Add a thin `SKILL.md` + optional CLI subcommand
4. Document risk level and evidence requirements
