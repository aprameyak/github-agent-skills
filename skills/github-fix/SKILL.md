---
name: github-fix
description: >
  Find small safe GitHub improvements (missing descriptions, topics, homepage links,
  straightforward presentation issues) and propose a batch for approval. Use when the
  user asks to fix the easy stuff or apply safe improvements. Never mutate without approval.
---

# github-fix

Find low-risk, evidence-backed improvements and present them as a batch proposal.

## Preconditions

1. `gh auth status` succeeds.
2. `github-agent` is on PATH.

## Workflow

```bash
github-agent fix
github-agent fix --json
github-agent propose /path/to/findings.json
```

Present a summary like:

```text
I found 12 safe improvements:

- 5 descriptions
- 4 topic sets
- 2 homepage links
- 1 profile detail
```

Then let the user:
- review everything,
- approve a subset,
- or approve the whole low-risk batch.

## Applying changes

Dry-run first:

```bash
github-agent apply-metadata --repo OWNER/NAME --description "Exact text"
```

Only with explicit approval:

```bash
github-agent apply-metadata --repo OWNER/NAME --description "Exact text" --execute
```

For topics:

```bash
github-agent apply-metadata --repo OWNER/NAME --topics "python,cli,github" --execute
```

## Rules

- **No remote mutations without approval.**
- Stay in low-risk metadata by default.
- README/content edits require branch → diff → approval → PR (use github-polish).
- Never delete repos, force-push, or change visibility.
- Draft description/topic text from evidence only.
