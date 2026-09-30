---
name: github-cleanup
description: >
  Conservative GitHub cleanup review. Use when the user asks to clean up GitHub,
  find clutter, empty/stale repos, old forks, duplicate-looking projects, or abandoned
  experiments. Suggests review candidates with evidence. Never deletes repositories.
---

# github-cleanup

Help the user spot repositories and clutter worth **reviewing**. Be conservative.

## Preconditions

1. `gh auth status` succeeds.
2. `github-agent` is on PATH.

## Workflow

```bash
github-agent cleanup
# or
github-agent cleanup --json
```

## Language rules (critical)

Say: **"Consider reviewing…"**

Do **not** say: **"Delete this."**

Never decide a repository is useless. People keep experiments, classwork, forks, and memories on purpose.

## What to surface

- Empty or near-empty repositories
- Stale projects (no pushes for a long time)
- Old forks
- Versioned groups (`app`, `app-v2`, `app-final`)
- Similar-looking duplicate names
- Archived repos that may still dominate the profile story

## Safety

- READ ONLY for this skill.
- Repository deletion is **out of scope** and must be refused.
- No force-push, archive-without-asking, or visibility changes.
- Always show evidence (size, last push date, fork parent, name group).

## Output style

Friendly, non-judgmental, actionable. Offer to help organize next steps (pins, READMEs, archival discussion) only with explicit approval for any mutation.
