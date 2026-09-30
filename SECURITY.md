# Security Policy

## Supported versions

Security fixes are accepted for the latest published release on `main`.

## Reporting a vulnerability

Please **do not** open a public issue for security problems that could expose credentials, private repository data, or unsafe mutation paths.

Email or privately message the maintainers via GitHub Security Advisories on this repository when available.

Include:

- a clear description of the issue
- steps to reproduce
- impact (credential leak, unintended mutation, etc.)
- suggested fix if you have one

## Scope notes

This project is local-first and uses your authenticated `gh` session.

- We never ask you to send us a GitHub token
- We do not operate a backend that stores your account data
- Destructive GitHub actions (delete repo, force-push, history rewrite) are intentionally out of scope

If you discover a path that mutates GitHub without an explicit approval step where one is required, treat that as a security issue.
