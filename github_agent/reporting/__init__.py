"""Human-friendly and JSON reporting helpers."""

from __future__ import annotations

import json
from typing import Any, TextIO

from github_agent.models.account import AccountSnapshot
from github_agent.models.findings import Finding, FindingsReport


def dumps(data: Any, *, pretty: bool = True) -> str:
    if pretty:
        return json.dumps(data, indent=2, sort_keys=False, default=str) + "\n"
    return json.dumps(data, separators=(",", ":"), default=str) + "\n"


def print_json(data: Any, *, stream: TextIO, pretty: bool = True) -> None:
    stream.write(dumps(data, pretty=pretty))


def format_checkup(report: FindingsReport, snapshot: AccountSnapshot) -> str:
    lines: list[str] = []
    lines.append("GitHub Checkup")
    lines.append("")
    repo_count = report.summary.get("repository_count", len(snapshot.repositories))
    lines.append(
        f"I looked through your profile and {repo_count} "
        f"repositor{'y' if repo_count == 1 else 'ies'}."
    )
    lines.append("")

    findings = report.findings
    if not findings:
        lines.append("Everything looks in solid shape from the checks I can run automatically.")
        lines.append("No urgent presentation or attention issues stood out.")
        return "\n".join(lines) + "\n"

    # Prefer presentation/profile/docs/cleanup for checkup narrative; keep attention capped.
    spotlight = [
        f
        for f in findings
        if f.category in {"profile", "presentation", "documentation", "cleanup"}
        or (f.category == "attention" and "actions" in f.tags)
    ]
    if not spotlight:
        spotlight = findings
    # For large accounts, keep the human summary tight
    limit = 8 if repo_count >= 40 else 12

    lines.append(f"I found {len(findings)} thing{'s' if len(findings) != 1 else ''} worth looking at:")
    lines.append("")
    quick = report.summary.get("quick_fixes", 0)
    docs = report.summary.get("documentation_gaps", 0)
    older = report.summary.get("older_projects", 0)
    failed = report.summary.get("failed_builds", 0)
    attention = report.summary.get("attention_items", 0)
    bullets = []
    if quick:
        bullets.append(f"{quick} quick fix{'es' if quick != 1 else ''}")
    if docs:
        bullets.append(
            f"{docs} project{'s' if docs != 1 else ''} that could be easier to understand"
        )
    if older:
        bullets.append(f"{older} older project{'s' if older != 1 else ''} worth reviewing")
    if failed:
        bullets.append(f"{failed} failed automated build{'s' if failed != 1 else ''}")
    if attention:
        bullets.append(f"{attention} attention item{'s' if attention != 1 else ''} (see github-today)")
    if not bullets:
        bullets.append(f"{len(findings)} note{'s' if len(findings) != 1 else ''}")
    for bullet in bullets:
        lines.append(f"- {bullet}")
    lines.append("")
    if repo_count >= 40:
        lines.append(
            "With an account this size, here are the highest-signal examples "
            "(not every individual item):"
        )
    else:
        lines.append("Most useful findings:")
    lines.append("")
    for finding in spotlight[:limit]:
        lines.extend(_format_finding(finding))
        lines.append("")
    remaining = max(0, len(findings) - min(limit, len(spotlight)))
    if remaining:
        lines.append(
            f"…plus more detail available via `github-agent fix`, "
            f"`github-agent cleanup`, and `github-agent today`."
        )
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def format_cleanup(report: FindingsReport) -> str:
    lines = ["GitHub Cleanup", ""]
    cleanup = [f for f in report.findings if f.category == "cleanup"]
    if not cleanup:
        lines.append("I didn't find obvious cleanup candidates with the current checks.")
        lines.append("Nothing looked empty, abandoned, or confusing enough to flag.")
        return "\n".join(lines) + "\n"
    lines.append(f"I found {len(cleanup)} item{'s' if len(cleanup) != 1 else ''} to consider reviewing:")
    lines.append("")
    lines.append("I'm not recommending deletion — only a closer look.")
    lines.append("")
    for finding in cleanup[:20]:
        lines.extend(_format_finding(finding, show_risk=False))
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def format_polish(report: FindingsReport) -> str:
    lines = ["GitHub Polish", ""]
    polish = [
        f
        for f in report.findings
        if f.category in {"presentation", "profile", "documentation", "consistency"}
    ]
    if not polish:
        lines.append("Your public presentation already looks fairly put together.")
        return "\n".join(lines) + "\n"
    lines.append(f"Here are {len(polish)} presentation improvements grounded in your repositories:")
    lines.append("")
    lines.append("For metadata changes I'll propose a preview and wait for your approval.")
    lines.append("For README/content changes I'll use a branch → diff → approval → PR flow.")
    lines.append("")
    for finding in polish[:20]:
        lines.extend(_format_finding(finding))
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def format_fix(report: FindingsReport) -> str:
    lines = ["GitHub Fix", ""]
    fixes = [f for f in report.findings if f.risk == "low"]
    if not fixes:
        lines.append("I didn't find low-risk safe fixes to batch right now.")
        return "\n".join(lines) + "\n"

    by_action: dict[str, list[Finding]] = {}
    for finding in fixes:
        key = finding.recommended_action or "other"
        by_action.setdefault(key, []).append(finding)

    lines.append(f"I found {len(fixes)} safe improvement{'s' if len(fixes) != 1 else ''}:")
    lines.append("")
    labels = {
        "add_description": "descriptions",
        "add_topics": "topic sets",
        "add_homepage": "homepage links",
        "fix_homepage": "broken homepage links",
        "complete_profile": "profile details",
        "add_readme": "README stubs (content — needs PR flow)",
    }
    for action, items in by_action.items():
        label = labels.get(action, action.replace("_", " "))
        lines.append(f"- {len(items)} {label}")
    lines.append("")
    lines.append("Nothing will change on GitHub until you approve a batch.")
    lines.append("")
    for finding in fixes[:15]:
        lines.extend(_format_finding(finding))
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def format_today(report: FindingsReport) -> str:
    lines = ["GitHub Today", ""]
    items = [f for f in report.findings if f.category == "attention"]
    if not items:
        lines.append("Nothing urgent is waiting for you right now.")
        lines.append("No open review requests, assigned issues, or failed builds stood out.")
        return "\n".join(lines) + "\n"

    reviews = [f for f in items if "review" in f.tags]
    builds = [f for f in items if "actions" in f.tags]
    deps = [f for f in items if "dependencies" in f.tags]
    own = [f for f in items if f.recommended_action == "check_own_pr" and f not in deps]
    issues = [f for f in items if f.recommended_action == "check_issue"]

    lines.append(
        f"You have {len(items)} thing{'s' if len(items) != 1 else ''} that may need attention:"
    )
    lines.append("")
    if reviews:
        lines.append(f"Review requests ({len(reviews)}):")
        for finding in reviews[:8]:
            lines.extend(_format_finding(finding, show_risk=False))
            lines.append("")
    if builds:
        lines.append(f"Failed automated builds ({len(builds)}):")
        for finding in builds[:8]:
            lines.extend(_format_finding(finding, show_risk=False))
            lines.append("")
    if own:
        lines.append(f"Your open pull requests ({len(own)}):")
        for finding in own[:8]:
            lines.extend(_format_finding(finding, show_risk=False))
            lines.append("")
    if deps:
        lines.append(f"Dependency update PRs ({len(deps)}):")
        for finding in deps[:5]:
            lines.extend(_format_finding(finding, show_risk=False))
            lines.append("")
    if issues:
        lines.append(f"Assigned issues ({len(issues)}):")
        if len(issues) > 8:
            lines.append(
                f"  Showing 8 of {len(issues)}. Many look like long-running course/project trackers."
            )
            lines.append("")
        for finding in issues[:8]:
            lines.extend(_format_finding(finding, show_risk=False))
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def format_recap(recap: dict) -> str:
    days = recap.get("since_days", 30)
    lines = [f"GitHub Recap — last {days} days", ""]
    for line in recap.get("summary_lines") or []:
        lines.append(f"- {line}")
    lines.append("")
    facts = recap.get("facts") or {}
    lines.append("Structured facts:")
    lines.append(f"- Repositories touched: {len(facts.get('repositories_touched') or [])}")
    lines.append(f"- Commits pushed (estimate): {facts.get('commits_pushed_estimate', 0)}")
    lines.append(f"- Pull requests opened: {facts.get('pull_requests_opened', 0)}")
    lines.append(f"- Issues opened: {facts.get('issues_opened', 0)}")
    lines.append(f"- Reviews: {facts.get('reviews', 0)}")
    lines.append(f"- Releases: {facts.get('releases', 0)}")
    langs = facts.get("languages_observed") or []
    if langs:
        lines.append(f"- Languages observed: {', '.join(langs)}")
    if facts.get("note"):
        lines.append("")
        lines.append(facts["note"])
    lines.append("")
    return "\n".join(lines)


def format_auth(status: Any) -> str:
    if getattr(status, "logged_in", False):
        scopes = ", ".join(status.scopes) if status.scopes else "(none reported)"
        return (
            "GitHub authentication looks good.\n"
            f"- Account: {status.username}\n"
            f"- Host: {status.host}\n"
            f"- Protocol: {status.protocol or 'unknown'}\n"
            f"- Scopes: {scopes}\n"
        )
    return (
        "GitHub CLI is not authenticated.\n"
        f"{status.message}\n"
        "Run: gh auth login\n"
    )


def format_snapshot_brief(snapshot: AccountSnapshot) -> str:
    p = snapshot.profile
    owned = [r for r in snapshot.repositories if not r.fork]
    forks = [r for r in snapshot.repositories if r.fork]
    archived = [r for r in snapshot.repositories if r.archived]
    lines = [
        f"Snapshot for @{snapshot.viewer_login}",
        f"Collected at: {snapshot.collected_at}",
        f"Repositories: {len(snapshot.repositories)} "
        f"({len(owned)} owned, {len(forks)} forks, {len(archived)} archived)",
        f"Open review/own PRs tracked: {len(snapshot.pull_requests)}",
        f"Assigned issues tracked: {len(snapshot.issues)}",
        f"Failed workflows tracked: {len(snapshot.workflow_runs)}",
        f"Activity events: {len(snapshot.activity)}",
    ]
    if p.bio:
        lines.append(f"Bio: {p.bio}")
    if snapshot.warnings:
        lines.append(f"Warnings: {len(snapshot.warnings)}")
    return "\n".join(lines) + "\n"


def _format_finding(finding: Finding, *, show_risk: bool = True) -> list[str]:
    prefix = ""
    if finding.heuristic:
        prefix = "[heuristic] "
    repo = f" ({finding.repository})" if finding.repository else ""
    lines = [f"• {prefix}{finding.title}{repo}"]
    lines.append(f"  {finding.explanation}")
    if finding.evidence:
        evidence_bits = []
        for key, value in list(finding.evidence.items())[:4]:
            evidence_bits.append(f"{key}={value!r}")
        lines.append(f"  Evidence: {', '.join(evidence_bits)}")
    if finding.recommended_action:
        lines.append(f"  Suggested next step: {finding.recommended_action.replace('_', ' ')}")
    if show_risk:
        lines.append(f"  Risk: {finding.risk} · confidence: {finding.confidence}")
    return lines
