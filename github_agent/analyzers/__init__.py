"""Deterministic analyzers that produce normalized findings."""

from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Iterable
from datetime import datetime, timezone

from github_agent.models.account import AccountSnapshot, Repository, days_since, utc_now_iso
from github_agent.models.findings import (
    Finding,
    FindingsReport,
    group_counts,
    sort_findings,
)

VERSION_SUFFIX_RE = re.compile(
    r"^(?P<base>.+?)[-_]?(?:v?\d+|final|copy|new|old|backup|test|wip)$",
    re.IGNORECASE,
)
DEP_LABELS = {"dependencies", "dependency", "dependabot", "renovate"}


def analyze(
    snapshot: AccountSnapshot,
    *,
    skill: str = "github-checkup",
    now: datetime | None = None,
) -> FindingsReport:
    current = now or datetime.now(timezone.utc)
    findings: list[Finding] = []

    if skill in {"github-checkup", "github-polish", "github-fix", "all"}:
        findings.extend(analyze_profile(snapshot))
        findings.extend(analyze_presentation(snapshot))

    if skill in {"github-checkup", "github-cleanup", "all"}:
        findings.extend(analyze_cleanup(snapshot, now=current))

    if skill in {"github-checkup", "github-today", "all"}:
        findings.extend(analyze_attention(snapshot, now=current))

    if skill == "github-fix":
        allowed_actions = {
            "add_description",
            "add_topics",
            "add_homepage",
            "fix_homepage",
            "complete_profile",
        }
        findings = [
            f
            for f in findings
            if f.recommended_action in allowed_actions
            and f.risk in {"read_only", "low"}
            and f.confidence != "low"
            and not f.heuristic
        ]

    findings = sort_findings(_dedupe(findings))
    summary = _build_summary(snapshot, findings, skill=skill)
    return FindingsReport(
        generated_at=utc_now_iso(),
        viewer_login=snapshot.viewer_login,
        skill=skill,
        findings=findings,
        summary=summary,
        meta={"warning_count": len(snapshot.warnings)},
    )


def analyze_profile(snapshot: AccountSnapshot) -> list[Finding]:
    findings: list[Finding] = []
    profile = snapshot.profile

    missing_fields = []
    if not (profile.name and profile.name.strip()):
        missing_fields.append("name")
    if not (profile.bio and profile.bio.strip()):
        missing_fields.append("bio")
    if not (profile.blog and str(profile.blog).strip()):
        missing_fields.append("website")

    if missing_fields:
        findings.append(
            Finding(
                id="profile:incomplete",
                category="profile",
                severity="suggestion",
                confidence="high",
                title="Your GitHub profile is missing a few details",
                explanation=(
                    "Profiles with a name, short bio, and website are easier for people "
                    f"to understand. Missing: {', '.join(missing_fields)}."
                ),
                evidence={"missing_fields": missing_fields},
                recommended_action="complete_profile",
                risk="low",
                tags=["profile"],
            )
        )

    if profile.profile_readme is False:
        findings.append(
            Finding(
                id="profile:missing-readme",
                category="profile",
                severity="suggestion",
                confidence="high",
                title="You don't have a profile README yet",
                explanation=(
                    "A profile README is a special repository that appears at the top of "
                    "your GitHub profile. It helps visitors quickly understand who you are."
                ),
                evidence={"profile_readme": False, "expected_repo": profile.login},
                recommended_action="add_profile_readme",
                risk="medium",
                tags=["profile", "readme"],
            )
        )

    return findings


def analyze_presentation(snapshot: AccountSnapshot) -> list[Finding]:
    findings: list[Finding] = []
    for repo in _owned_active(snapshot.repositories):
        if not repo.description or not repo.description.strip():
            findings.append(
                Finding(
                    id=f"missing-description:{repo.name}",
                    category="presentation",
                    severity="suggestion",
                    confidence="high",
                    repository=repo.name,
                    title=f"“{repo.name}” has no description",
                    explanation=(
                        "A one-line description helps people (and search) understand "
                        "what this project is."
                    ),
                    evidence={"description": repo.description, "language": repo.language},
                    recommended_action="add_description",
                    risk="low",
                    tags=["metadata"],
                )
            )

        if not repo.topics:
            findings.append(
                Finding(
                    id=f"missing-topics:{repo.name}",
                    category="presentation",
                    severity="suggestion",
                    confidence="high",
                    repository=repo.name,
                    title=f"“{repo.name}” has no topics",
                    explanation=(
                        "Topics are searchable labels (like language or purpose) that make "
                        "a project easier to discover."
                    ),
                    evidence={"topics": repo.topics, "language": repo.language},
                    recommended_action="add_topics",
                    risk="low",
                    tags=["metadata"],
                )
            )

        if repo.has_readme is False and not repo.fork:
            findings.append(
                Finding(
                    id=f"missing-readme:{repo.name}",
                    category="documentation",
                    severity="attention",
                    confidence="high",
                    repository=repo.name,
                    title=f"“{repo.name}” is missing a README",
                    explanation=(
                        "Without a README, visitors have to guess what the project does "
                        "and how to get started."
                    ),
                    evidence={"has_readme": False, "size": repo.size},
                    recommended_action="add_readme",
                    risk="medium",
                    tags=["readme"],
                )
            )

        if repo.has_pages and not (repo.homepage and repo.homepage.strip()):
            findings.append(
                Finding(
                    id=f"missing-homepage:{repo.name}",
                    category="presentation",
                    severity="suggestion",
                    confidence="medium",
                    repository=repo.name,
                    title=f"“{repo.name}” may be missing a homepage link",
                    explanation=(
                        "This repository has GitHub Pages enabled, but no homepage URL "
                        "is set on the repository."
                    ),
                    evidence={
                        "has_pages": True,
                        "homepage": repo.homepage,
                        "suggested": f"https://{snapshot.viewer_login}.github.io/{repo.name}/",
                    },
                    recommended_action="add_homepage",
                    risk="low",
                    heuristic=True,
                    tags=["metadata", "pages"],
                )
            )

        if repo.broken_homepage is True:
            findings.append(
                Finding(
                    id=f"broken-homepage:{repo.name}",
                    category="presentation",
                    severity="attention",
                    confidence="medium",
                    repository=repo.name,
                    title=f"Homepage link for “{repo.name}” looks broken",
                    explanation="The homepage URL did not respond successfully when checked.",
                    evidence={"homepage": repo.homepage},
                    recommended_action="fix_homepage",
                    risk="low",
                    tags=["metadata"],
                )
            )

        if (
            not repo.fork
            and not repo.private
            and repo.stargazers_count >= 1
            and not repo.license_spdx
            and repo.license_spdx != "NOASSERTION"
            and repo.size > 5
            and repo.has_readme is not False
        ):
            findings.append(
                Finding(
                    id=f"missing-license:{repo.name}",
                    category="presentation",
                    severity="info",
                    confidence="medium",
                    repository=repo.name,
                    title=f"“{repo.name}” has no license file detected",
                    explanation=(
                        "Public projects without a license can be harder for others "
                        "to reuse. Only add one if you intend to share the work."
                    ),
                    evidence={"license": repo.license_spdx, "visibility": repo.visibility},
                    recommended_action="consider_license",
                    risk="medium",
                    tags=["license"],
                )
            )

    return findings


def analyze_cleanup(snapshot: AccountSnapshot, *, now: datetime) -> list[Finding]:
    findings: list[Finding] = []
    repos = snapshot.repositories

    for repo in repos:
        if repo.archived:
            continue

        if repo.size == 0 and not repo.fork:
            findings.append(
                Finding(
                    id=f"empty-repo:{repo.name}",
                    category="cleanup",
                    severity="suggestion",
                    confidence="high",
                    repository=repo.name,
                    title=f"Consider reviewing empty repository “{repo.name}”",
                    explanation=(
                        "This repository appears empty (no recorded content size). "
                        "It may be unfinished, created by mistake, or waiting for a first push."
                    ),
                    evidence={"size": repo.size, "pushed_at": repo.pushed_at},
                    recommended_action="review_empty_repo",
                    risk="read_only",
                    tags=["empty"],
                )
            )
        elif repo.size <= 5 and not repo.fork and repo.has_readme is False:
            findings.append(
                Finding(
                    id=f"near-empty-repo:{repo.name}",
                    category="cleanup",
                    severity="suggestion",
                    confidence="medium",
                    repository=repo.name,
                    title=f"Consider reviewing sparse repository “{repo.name}”",
                    explanation=(
                        "This repository looks nearly empty and has no README. "
                        "It may be an abandoned experiment — or a project you still plan to finish."
                    ),
                    evidence={"size": repo.size, "has_readme": repo.has_readme},
                    recommended_action="review_sparse_repo",
                    risk="read_only",
                    heuristic=True,
                    tags=["sparse"],
                )
            )

        age = days_since(repo.pushed_at, now=now)
        if age is not None and age >= 365 and not repo.fork and not repo.archived:
            findings.append(
                Finding(
                    id=f"stale-repo:{repo.name}",
                    category="cleanup",
                    severity="info",
                    confidence="high",
                    repository=repo.name,
                    title=f"“{repo.name}” hasn't been updated in over a year",
                    explanation=(
                        f"Last push was about {age} days ago. Consider whether you still "
                        "want it featured prominently, archived, or refreshed."
                    ),
                    evidence={"pushed_at": repo.pushed_at, "days_since_push": age},
                    recommended_action="review_stale_repo",
                    risk="read_only",
                    tags=["stale"],
                )
            )

        if repo.fork and age is not None and age >= 180:
            findings.append(
                Finding(
                    id=f"old-fork:{repo.name}",
                    category="cleanup",
                    severity="info",
                    confidence="medium",
                    repository=repo.name,
                    title=f"Consider reviewing old fork “{repo.name}”",
                    explanation=(
                        "This fork hasn't been updated recently. Some people keep forks "
                        "for reference; others prefer to remove ones they no longer need."
                    ),
                    evidence={
                        "fork": True,
                        "parent": repo.parent_full_name,
                        "pushed_at": repo.pushed_at,
                        "days_since_push": age,
                    },
                    recommended_action="review_old_fork",
                    risk="read_only",
                    heuristic=True,
                    tags=["fork"],
                )
            )

    # Versioned / duplicate-looking groups
    by_name = {r.name.lower(): r for r in repos if not r.archived}
    groups: dict[str, set[str]] = defaultdict(set)
    for repo in repos:
        if repo.archived:
            continue
        base = _version_base(repo.name)
        if base:
            groups[base.lower()].add(repo.name)
            # Include the bare base repo if it exists
            if base.lower() in by_name:
                groups[base.lower()].add(by_name[base.lower()].name)
        # Also: name is prefix of another with separator
        for other in repos:
            if other.archived or other.name == repo.name:
                continue
            left, right = repo.name.lower(), other.name.lower()
            if right.startswith((left + "-", left + "_")):
                suffix = right[len(left) + 1 :]
                if re.fullmatch(r"(?:v?\d+|final|copy|new|old|backup|test|wip)(?:[-_].+)?", suffix, re.IGNORECASE):
                    groups[left].add(repo.name)
                    groups[left].add(other.name)

    for base, names in groups.items():
        if len(names) < 2:
            continue
        ordered = sorted(names)
        findings.append(
            Finding(
                id=f"versioned-group:{base}",
                category="cleanup",
                severity="suggestion",
                confidence="medium",
                title=f"Consider reviewing related repositories: {', '.join(ordered)}",
                explanation=(
                    "These repository names look like versions or copies of the same idea "
                    "(for example app / app-v2 / app-final). That can be intentional — "
                    "or leftover from experiments."
                ),
                evidence={"base": base, "repositories": ordered},
                recommended_action="review_versioned_group",
                risk="read_only",
                heuristic=True,
                tags=["duplicates"],
            )
        )

    # Near-duplicate names (edit-distance light heuristic via shared prefix)
    active = [r for r in repos if not r.archived and not r.fork]
    similar_pairs: list[tuple[str, str]] = []
    for i, left in enumerate(active):
        for right in active[i + 1 :]:
            if _similar_names(left.name, right.name):
                # Skip pairs already explained by a versioned group
                if _version_base(left.name) or _version_base(right.name):
                    continue
                if any(
                    left.name in names and right.name in names
                    for names in groups.values()
                    if len(names) >= 2
                ):
                    continue
                pair = tuple(sorted([left.name, right.name]))
                similar_pairs.append(pair)  # type: ignore[arg-type]
    # Cap noise on large accounts
    for pair in similar_pairs[:25]:
        findings.append(
            Finding(
                id=f"similar-names:{pair[0]}:{pair[1]}",
                category="cleanup",
                severity="info",
                confidence="low",
                title=f"Repositories “{pair[0]}” and “{pair[1]}” have similar names",
                explanation=(
                    "Similar names sometimes mean related projects, renames, "
                    "or accidental duplicates. Worth a quick look."
                ),
                evidence={"repositories": list(pair)},
                recommended_action="review_similar_repos",
                risk="read_only",
                heuristic=True,
                tags=["duplicates"],
            )
        )

    archived_visible = [r for r in repos if r.archived]
    if archived_visible and len(archived_visible) >= 3:
        findings.append(
            Finding(
                id="archived:many-visible",
                category="cleanup",
                severity="info",
                confidence="high",
                title=f"You have {len(archived_visible)} archived repositories",
                explanation=(
                    "Archived projects are read-only. They still appear on your profile "
                    "unless you pin other repositories or organize them carefully."
                ),
                evidence={"count": len(archived_visible), "names": [r.name for r in archived_visible[:20]]},
                recommended_action="review_archived",
                risk="read_only",
                tags=["archived"],
            )
        )

    return findings


def analyze_attention(snapshot: AccountSnapshot, *, now: datetime) -> list[Finding]:
    findings: list[Finding] = []

    review_prs = [p for p in snapshot.pull_requests if p.is_review_request]
    own_prs = [p for p in snapshot.pull_requests if p.is_own]
    assigned = list(snapshot.issues)

    for pr in review_prs:
        findings.append(
            Finding(
                id=f"review-request:{pr.repository}#{pr.number}",
                category="attention",
                severity="attention",
                confidence="high",
                repository=pr.repository,
                title=f"Review requested: {pr.title}",
                explanation="Someone asked you to review this pull request.",
                evidence={
                    "number": pr.number,
                    "url": pr.html_url,
                    "draft": pr.draft,
                    "updated_at": pr.updated_at,
                },
                recommended_action="review_pr",
                risk="read_only",
                tags=["pr", "review"],
            )
        )

    for pr in own_prs:
        labels = {x.lower() for x in pr.labels}
        is_dep = bool(labels & DEP_LABELS) or "dependabot" in (pr.author or "").lower()
        age = days_since(pr.updated_at, now=now)
        severity = "info" if is_dep else "attention"
        title = f"Your open pull request: {pr.title}"
        if is_dep:
            title = f"Dependency update waiting: {pr.title}"
        findings.append(
            Finding(
                id=f"own-pr:{pr.repository}#{pr.number}",
                category="attention",
                severity=severity,
                confidence="high",
                repository=pr.repository,
                title=title,
                explanation=(
                    "This pull request is still open."
                    + (f" Last update about {age} days ago." if age is not None else "")
                ),
                evidence={
                    "number": pr.number,
                    "url": pr.html_url,
                    "draft": pr.draft,
                    "author": pr.author,
                    "labels": pr.labels,
                    "dependency_update": is_dep,
                },
                recommended_action="check_own_pr",
                risk="read_only",
                tags=["pr"] + (["dependencies"] if is_dep else []),
            )
        )

    for issue in assigned:
        findings.append(
            Finding(
                id=f"assigned-issue:{issue.repository}#{issue.number}",
                category="attention",
                severity="attention",
                confidence="high",
                repository=issue.repository,
                title=f"Assigned issue: {issue.title}",
                explanation="This open issue is assigned to you.",
                evidence={"number": issue.number, "url": issue.html_url, "labels": issue.labels},
                recommended_action="check_issue",
                risk="read_only",
                tags=["issue"],
            )
        )

    for run in snapshot.workflow_runs:
        findings.append(
            Finding(
                id=f"failed-workflow:{run.repository}:{run.name}",
                category="attention",
                severity="attention",
                confidence="high",
                repository=run.repository,
                title=f"Automated build failed in {run.repository.split('/')[-1]}",
                explanation=(
                    "Your project's automated checks reported a failure. "
                    f"Technical detail: workflow “{run.name}” concluded with {run.conclusion}."
                ),
                evidence={
                    "workflow": run.name,
                    "conclusion": run.conclusion,
                    "url": run.html_url,
                    "branch": run.head_branch,
                },
                recommended_action="fix_workflow",
                risk="read_only",
                tags=["actions", "ci"],
            )
        )

    return findings


def build_recap(
    snapshot: AccountSnapshot,
    *,
    since_days: int = 30,
    now: datetime | None = None,
) -> dict:
    current = now or datetime.now(timezone.utc)
    cutoff = current.timestamp() - (since_days * 86400)

    events = []
    for event in snapshot.activity:
        dt = _parse_ts(event.created_at)
        if dt is None:
            continue
        if dt.timestamp() < cutoff:
            continue
        events.append(event)

    repos_touched: dict[str, int] = defaultdict(int)
    commits = 0
    prs_opened = 0
    prs_merged = 0
    issues_opened = 0
    reviews = 0
    releases = 0
    comments = 0

    for event in events:
        if event.repository:
            repos_touched[event.repository] += 1
        raw = event.raw_type or ""
        if raw == "PushEvent":
            match = re.search(r"Pushed (\d+)", event.summary)
            commits += int(match.group(1)) if match else 1
        elif raw == "PullRequestEvent":
            if "opened" in event.summary.lower():
                prs_opened += 1
            if "closed" in event.summary.lower() and "merge" in event.summary.lower():
                prs_merged += 1
            # payload-normalized summaries may say Merged via action closed + merged elsewhere;
            # count closed PRs cautiously from summary text
            if event.summary.lower().startswith("closed"):
                prs_merged += 0  # unknown without merge flag; keep factual
        elif raw == "IssuesEvent" and event.summary.lower().startswith("opened"):
            issues_opened += 1
        elif raw == "PullRequestReviewEvent":
            reviews += 1
        elif raw == "ReleaseEvent":
            releases += 1
        elif raw in {"IssueCommentEvent", "PullRequestReviewCommentEvent"}:
            comments += 1

    languages = sorted(
        {
            r.language
            for r in snapshot.repositories
            if r.language and any(
                event.repository == r.full_name or (event.repository or "").endswith("/" + r.name)
                for event in events
            )
        }
    )

    facts = {
        "period_days": since_days,
        "events_counted": len(events),
        "repositories_touched": sorted(repos_touched.keys(), key=lambda k: (-repos_touched[k], k)),
        "repository_touch_counts": dict(sorted(repos_touched.items(), key=lambda kv: (-kv[1], kv[0]))),
        "commits_pushed_estimate": commits,
        "pull_requests_opened": prs_opened,
        "issues_opened": issues_opened,
        "reviews": reviews,
        "releases": releases,
        "comments": comments,
        "languages_observed": languages,
        "note": (
            "Counts are based on GitHub's public activity feed for your account. "
            "They may undercount private activity or events outside the recent feed window."
        ),
    }

    highlights = []
    if facts["repositories_touched"]:
        top = facts["repositories_touched"][:5]
        highlights.append(f"You touched {len(facts['repositories_touched'])} repositories, including {', '.join(t.split('/')[-1] for t in top)}.")
    if commits:
        highlights.append(f"You pushed about {commits} commit(s) (from activity events).")
    if prs_opened:
        highlights.append(f"You opened {prs_opened} pull request(s).")
    if reviews:
        highlights.append(f"You left {reviews} pull request review(s).")
    if releases:
        highlights.append(f"You published {releases} release(s).")
    if issues_opened:
        highlights.append(f"You opened {issues_opened} issue(s).")
    if not highlights:
        highlights.append("No recent public activity events were found for this period.")

    return {
        "generated_at": utc_now_iso(),
        "viewer_login": snapshot.viewer_login,
        "since_days": since_days,
        "facts": facts,
        "summary_lines": highlights,
        "evidence_events": [
            {
                "type": e.type,
                "repository": e.repository,
                "created_at": e.created_at,
                "summary": e.summary,
                "url": e.url,
            }
            for e in events[:100]
        ],
    }


def _build_summary(snapshot: AccountSnapshot, findings: list[Finding], *, skill: str) -> dict:
    quick = [f for f in findings if f.risk == "low" and f.severity == "suggestion"]
    docs = [f for f in findings if f.category == "documentation"]
    stale = [f for f in findings if "stale" in f.tags or f.id.startswith("stale-")]
    failed = [f for f in findings if "actions" in f.tags]
    attention = [f for f in findings if f.category == "attention"]
    return {
        "skill": skill,
        "repository_count": len(snapshot.repositories),
        "finding_count": len(findings),
        "by_category": group_counts(findings),
        "quick_fixes": len(quick),
        "documentation_gaps": len(docs),
        "older_projects": len(stale),
        "failed_builds": len(failed),
        "attention_items": len(attention),
        "heuristic_count": sum(1 for f in findings if f.heuristic),
    }


def _owned_active(repositories: Iterable[Repository]) -> list[Repository]:
    return [r for r in repositories if not r.archived and not r.fork]


def _version_base(name: str) -> str | None:
    match = VERSION_SUFFIX_RE.match(name)
    if not match:
        return None
    base = match.group("base").rstrip("-_")
    if len(base) < 2:
        return None
    # Require that suffix actually changed something meaningful
    if base.lower() == name.lower():
        return None
    return base


def _similar_names(a: str, b: str) -> bool:
    left, right = a.lower(), b.lower()
    if left == right:
        return False
    # Numeric course/project series are handled by versioned-group logic
    if re.search(r"\d+$", left) and re.search(r"\d+$", right):
        stem_l = re.sub(r"\d+$", "", left)
        stem_r = re.sub(r"\d+$", "", right)
        if stem_l and stem_l == stem_r:
            return False
    if left in right or right in left:
        return min(len(left), len(right)) >= 4
    prefix = 0
    for x, y in zip(left, right):
        if x != y:
            break
        prefix += 1
    return prefix >= 6 and abs(len(left) - len(right)) <= 2


def _dedupe(findings: list[Finding]) -> list[Finding]:
    seen: set[str] = set()
    out: list[Finding] = []
    for finding in findings:
        if finding.id in seen:
            continue
        seen.add(finding.id)
        out.append(finding)
    return out


def _parse_ts(value: str | None) -> datetime | None:
    if not value:
        return None
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None
