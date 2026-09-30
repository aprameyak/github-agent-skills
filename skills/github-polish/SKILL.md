---
name: github-polish
description: >
  Improve GitHub presentation: profile, profile README, descriptions, topics,
  homepage URLs, README intros, and consistency. Use when the user asks to make
  GitHub look better, look put together, or polish their profile/repos.
---

# github-polish

Make the user's GitHub look put together using **evidence from their actual repositories**.

## Preconditions

1. `gh auth status` succeeds.
2. `github-agent` is on PATH.

## Workflow

1. Analyze presentation gaps:
   ```bash
   github-agent polish
   github-agent polish --json
   ```
2. For each improvement:
   - Infer suggestions only from repository evidence (README preview, language, topics, homepage, code signals).
   - **Never fabricate** features, stack, or impact.
3. Apply changes with the correct safety lane:

### Metadata (description / topics / homepage)

1. Propose exact new values.
2. Preview (`github-agent apply-metadata ...` without `--execute`).
3. Get explicit user approval.
4. Apply with `--execute`.

### Content (README / profile README)

1. Create a branch.
2. Modify locally.
3. Show the diff.
4. Get approval.
5. Push and open a pull request with `gh`.

## Rules

- Do not silently edit the default branch for content changes.
- Do not invent project capabilities.
- Prefer small, accurate descriptions over marketing fluff.
- Topics should be real, conventional, and grounded in evidence.
- Keep language approachable; offer technical detail on request.
