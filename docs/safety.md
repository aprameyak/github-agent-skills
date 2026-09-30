# Safety model

## Risk levels

| Level | Meaning | Default behavior |
| --- | --- | --- |
| `read_only` | Observation only | Automatic |
| `low` | Reversible metadata (description, topics, homepage) | Preview + approval |
| `medium` | Content changes (README, profile README) | Branch → diff → approval → PR |
| `high` | Significant remote actions | Explicit individual approval |
| `forbidden` | Destructive / irreversible | Not implemented |

## Hard rules for v1

- No repository deletion
- No force-push
- No history rewriting
- No silent archival
- No silent visibility changes
- No sending GitHub credentials to a third-party backend

## Mutation flow

### Metadata

```text
proposal → dry-run preview → user approval → github-agent apply-metadata --execute
```

### Content

```text
branch → local modify → show diff → approval → push → pull request
```

## Agent guidance

Skills must refuse unsafe requests and keep using approachable language:

> “I can help you review that repository. I won’t delete it.”
