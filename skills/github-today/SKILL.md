---
name: github-today
description: >
  Account-wide briefing of what needs attention on GitHub: review requests, open PRs,
  assigned issues, failed automated builds, dependency updates, and stale work.
  Use when the user asks what needs attention, what's waiting, or "GitHub today".
---

# github-today

Give an actionable briefing of what needs the user's attention — without inventing urgency.

## Preconditions

1. `gh auth status` succeeds.
2. `github-agent` is on PATH.

## Workflow

```bash
github-agent today
github-agent today --json
```

## Output adaptation

- One outstanding item → simple direct answer.
- Many items → prioritize review requests and failed builds before routine dependency noise.
- Beginner accounts → plain language ("Your automated build is failing") then optional technical detail.

## Rules

- READ ONLY.
- Do **not** invent urgency or deadlines.
- Separate clearly:
  - review requests
  - the user's open PRs
  - assigned issues
  - failed automated builds
  - dependency update PRs
- If permissions block a signal, say so honestly (see snapshot warnings).
- No mutations.
