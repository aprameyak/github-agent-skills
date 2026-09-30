---
name: github-recap
description: >
  Evidence-backed recap of what the user has done on GitHub over a time period
  (7d, 30d, 90d, year). Use when asked for a monthly recap, "what have I done on
  GitHub", activity summary, or contribution highlights. Never fabricate impact.
---

# github-recap

Summarize what the user **actually** did on GitHub in a period, with facts and a readable narrative tied to evidence.

## Preconditions

1. `gh auth status` succeeds.
2. `github-agent` is on PATH.

## Workflow

```bash
github-agent recap --since 30d
github-agent recap --since 7d --json
github-agent recap --since 90d
github-agent recap --since year
```

## Output

Provide:
1. Short readable highlights.
2. Structured facts (repos touched, commits estimate, PRs, issues, reviews, releases, languages observed).
3. Links/evidence from events when useful.

Future-friendly: the CLI already emits JSON suitable for Markdown/JSON consumers.

## Rules

- Never fabricate impact, awards, growth, or technologies without evidence.
- Tie claims to repositories, PRs, issues, releases, or activity events.
- Mention that GitHub's activity feed can undercount (especially private/out-of-window events).
- READ ONLY.
