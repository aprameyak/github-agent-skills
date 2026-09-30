---
name: github-checkup
description: >
  Read-only GitHub account checkup. Use when the user asks to check their GitHub,
  "how's my GitHub", review their profile/repos presentation, or run a GitHub checkup.
  Produces friendly, evidence-backed findings without changing anything on GitHub.
---

# github-checkup

Help the user understand how their GitHub account is doing — presentation, clarity, and a few attention items — without judging them as a developer.

## Preconditions

1. `git` and `gh` are installed.
2. `gh auth status` succeeds.
3. `github-agent` is installed (`pip install -e .` from this repo, or via `./install.sh`).

## Workflow

1. Confirm authentication:
   ```bash
   github-agent auth-check --json
   ```
2. Collect + analyze (read-only):
   ```bash
   github-agent checkup
   ```
   For machine-readable output:
   ```bash
   github-agent checkup --json
   ```
3. Optionally reuse a snapshot:
   ```bash
   github-agent snapshot --out /tmp/gh-snapshot.json
   github-agent checkup --snapshot /tmp/gh-snapshot.json
   ```

## Output style

Lead with a friendly summary like:

```text
GitHub Checkup

I looked through your profile and 12 repositories.

I found 7 things worth looking at:

- 3 quick fixes
- 2 projects that could be easier to understand
- 1 older project worth reviewing
- 1 failed automated build
```

Then explain the most useful findings with evidence.

Adapt to account size:
- Few repos → keep it short and concrete.
- Many repos → prioritize; do not dump enterprise metric walls.

## Rules

- READ ONLY. Never mutate GitHub.
- Never invent accomplishments, technologies, or metrics.
- Never rate the person as a developer. Talk about account health and presentation.
- Prefer plain language. Add technical detail only after the plain explanation.
- Every recommendation must cite evidence from the CLI/JSON output.
- Do not clone every repository. Rely on `github-agent` progressive inspection.
