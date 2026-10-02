# Contributing a new skill

You can add skills without rewriting the core.

## 1. Pick a job

Choose a clear user job that reuses (or narrowly extends) existing collectors and analyzers.

## 2. Prefer shared data

Reuse `AccountSnapshot` fields when possible. Only extend collectors when a user-facing capability needs new reliable signals.

## 3. Add deterministic analysis first

Put objective detection in `github_agent/analyzers/`.
Leave semantic writing (descriptions, README prose) to the coding agent.

## 4. Add a CLI entrypoint if useful

Humans and agents should be able to run the skill without an LLM:

```bash
github-agent <command> --json
```

## 5. Write `skills/<name>/SKILL.md`

Include:

- trigger description
- exact CLI commands
- output style
- safety / approval rules
- failure behavior

## 6. Tests

Add fixtures + analyzer/CLI tests. Never mutate real GitHub in CI.
