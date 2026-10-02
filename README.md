# github-agent-skills

Local CLI + skills that use your existing `gh` auth to inspect and tidy a GitHub account.

```bash
gh auth login
git clone https://github.com/aprameyak/github-agent-skills.git
cd github-agent-skills
./install.sh
export PATH="$HOME/.local/bin:$PATH"
github-agent checkup
```

Skills: `github-checkup` `github-cleanup` `github-polish` `github-fix` `github-today` `github-recap`

Read-only by default. No repo delete / force-push. Docs in `docs/`.

## License

MIT
