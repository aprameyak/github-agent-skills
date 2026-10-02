"""Account snapshot collectors using authenticated `gh`."""

from __future__ import annotations

import base64
import concurrent.futures
import re
import sys
from collections.abc import Callable
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from github_agent import gh
from github_agent.models.account import (
    AccountSnapshot,
    ActivityEvent,
    CollectionWarning,
    IssueSummary,
    Profile,
    PullRequestSummary,
    Repository,
    WorkflowRunSummary,
    utc_now_iso,
)

ProgressCallback = Callable[[str], None]


def _progress(cb: ProgressCallback | None, message: str) -> None:
    if cb:
        cb(message)


def collect_snapshot(
    *,
    username: str | None = None,
    include_private: bool = True,
    enrich_readmes: bool = True,
    enrich_workflows: bool = True,
    check_homepages: bool = False,
    max_readme_checks: int = 40,
    max_workflow_checks: int = 30,
    activity_pages: int = 3,
    progress: ProgressCallback | None = None,
) -> AccountSnapshot:
    warnings: list[CollectionWarning] = []
    _progress(progress, "Checking authentication…")
    login = username or gh.current_username()

    _progress(progress, f"Loading profile for @{login}…")
    profile_data = gh.api(f"/users/{login}")
    if not isinstance(profile_data, dict):
        raise gh.GhError("Unexpected profile response", command=["gh", "api", f"/users/{login}"])
    profile = Profile.from_api(profile_data)

    # Authenticated user endpoint has richer private fields when login matches viewer
    try:
        viewer = gh.api("/user")
        if isinstance(viewer, dict) and viewer.get("login") == login:
            profile = Profile.from_api(viewer)
    except gh.GhError as exc:
        warnings.append(CollectionWarning(code="viewer_enrich_failed", message=str(exc)))

    _progress(progress, "Checking for a profile README…")
    profile.profile_readme, profile.profile_readme_preview = _fetch_readme(
        login, login, warnings=warnings
    )

    _progress(progress, "Collecting repositories…")
    repositories = _collect_repositories(login, include_private=include_private, warnings=warnings)
    _progress(progress, f"Found {len(repositories)} repositories.")

    if enrich_readmes:
        _progress(progress, "Checking READMEs for key repositories…")
        _enrich_readmes(repositories, max_checks=max_readme_checks, warnings=warnings)

    if enrich_workflows:
        _progress(progress, "Checking recent automated builds…")
        workflow_runs = _collect_workflow_failures(
            repositories, max_checks=max_workflow_checks, warnings=warnings
        )
    else:
        workflow_runs = []

    if check_homepages:
        _progress(progress, "Checking homepage links…")
        _check_homepages(repositories, warnings=warnings)

    _progress(progress, "Collecting pull requests and issues that need attention…")
    pull_requests, issues = _collect_attention_items(login, warnings=warnings)

    _progress(progress, "Collecting recent activity…")
    activity = _collect_activity(login, pages=activity_pages, warnings=warnings)

    return AccountSnapshot(
        collected_at=utc_now_iso(),
        viewer_login=login,
        profile=profile,
        repositories=repositories,
        pull_requests=pull_requests,
        issues=issues,
        workflow_runs=workflow_runs,
        activity=activity,
        warnings=warnings,
        meta={
            "include_private": include_private,
            "enrich_readmes": enrich_readmes,
            "enrich_workflows": enrich_workflows,
            "check_homepages": check_homepages,
            "repo_count": len(repositories),
        },
    )


def _collect_repositories(
    login: str,
    *,
    include_private: bool,
    warnings: list[CollectionWarning],
) -> list[Repository]:
    repos: list[Repository] = []
    try:
        # Prefer authenticated listing so private repos are included when permitted.
        viewer = gh.api("/user")
        if isinstance(viewer, dict) and viewer.get("login") == login and include_private:
            raw = gh.api("/user/repos?per_page=100&affiliation=owner", paginate=True)
        else:
            raw = gh.api(f"/users/{login}/repos?per_page=100&type=owner", paginate=True)
    except gh.GhError as exc:
        warnings.append(CollectionWarning(code="repos_failed", message=str(exc)))
        return []

    if not isinstance(raw, list):
        warnings.append(
            CollectionWarning(code="repos_unexpected", message="Repository list was not an array.")
        )
        return []

    for item in raw:
        if not isinstance(item, dict):
            continue
        # Skip repos not owned by the user when affiliation returns collaborator repos
        owner = (item.get("owner") or {}).get("login")
        if owner and owner != login:
            continue
        repos.append(Repository.from_api(item))
    repos.sort(key=lambda r: (r.archived, r.fork, -(r.stargazers_count or 0), r.name.lower()))
    return repos


def _fetch_readme(
    owner: str,
    repo: str,
    *,
    warnings: list[CollectionWarning] | None = None,
) -> tuple[bool | None, str | None]:
    try:
        data = gh.api(f"/repos/{owner}/{repo}/readme")
    except gh.GhError as exc:
        message = str(exc).lower()
        if "404" in message or "not found" in message:
            return False, None
        if warnings is not None:
            warnings.append(
                CollectionWarning(
                    code="readme_fetch_failed",
                    message=str(exc),
                    repository=f"{owner}/{repo}",
                )
            )
        return None, None

    if not isinstance(data, dict):
        return None, None
    content = data.get("content")
    encoding = data.get("encoding")
    preview = None
    if isinstance(content, str) and encoding == "base64":
        try:
            decoded = base64.b64decode(content).decode("utf-8", errors="replace")
            preview = decoded[:800]
        except (ValueError, UnicodeError):
            preview = None
    return True, preview


def _enrich_readmes(
    repositories: list[Repository],
    *,
    max_checks: int,
    warnings: list[CollectionWarning],
) -> None:
    candidates = [
        r
        for r in repositories
        if not r.archived and not r.fork and r.size > 0
    ][:max_checks]
    # Also check empty-looking repos (size 0) up to a small budget
    empties = [r for r in repositories if not r.archived and r.size == 0][:10]
    seen = {r.full_name for r in candidates}
    for repo in empties:
        if repo.full_name not in seen:
            candidates.append(repo)

    def work(repo: Repository) -> None:
        owner, _, name = repo.full_name.partition("/")
        has_readme, preview = _fetch_readme(owner, name, warnings=warnings)
        repo.has_readme = has_readme
        repo.readme_preview = preview

    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        list(pool.map(work, candidates))


def _collect_workflow_failures(
    repositories: list[Repository],
    *,
    max_checks: int,
    warnings: list[CollectionWarning],
) -> list[WorkflowRunSummary]:
    runs: list[WorkflowRunSummary] = []
    candidates = [
        r
        for r in repositories
        if not r.archived and not r.fork and r.size > 0
    ][:max_checks]

    def work(repo: Repository) -> WorkflowRunSummary | None:
        try:
            data = gh.api(
                f"/repos/{repo.full_name}/actions/runs?per_page=1&status=completed"
            )
        except gh.GhError as exc:
            message = str(exc).lower()
            if "404" in message or "403" in message or "disabled" in message:
                return None
            warnings.append(
                CollectionWarning(
                    code="workflow_fetch_failed",
                    message=str(exc),
                    repository=repo.full_name,
                )
            )
            return None
        if not isinstance(data, dict):
            return None
        items = data.get("workflow_runs") or []
        if not items:
            return None
        item = items[0]
        conclusion = item.get("conclusion")
        repo.workflow_conclusion = conclusion
        repo.workflow_name = item.get("name")
        if conclusion in {"failure", "timed_out", "cancelled"}:
            return WorkflowRunSummary(
                repository=repo.full_name,
                name=item.get("name") or "workflow",
                conclusion=conclusion,
                status=item.get("status"),
                html_url=item.get("html_url"),
                head_branch=item.get("head_branch"),
                created_at=item.get("created_at"),
                updated_at=item.get("updated_at"),
            )
        return None

    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        for result in pool.map(work, candidates):
            if result is not None:
                runs.append(result)
    return runs


def _check_homepages(
    repositories: list[Repository],
    *,
    warnings: list[CollectionWarning],
) -> None:
    def check(repo: Repository) -> None:
        url = (repo.homepage or "").strip()
        if not url:
            return
        if not re.match(r"^https?://", url, re.IGNORECASE):
            url = "https://" + url
        try:
            req = Request(url, method="HEAD", headers={"User-Agent": "github-agent-skills/0.1"})
            with urlopen(req, timeout=5) as resp:
                code = getattr(resp, "status", 200)
                repo.broken_homepage = code >= 400
        except HTTPError as exc:
            repo.broken_homepage = exc.code >= 400
        except (URLError, TimeoutError, ValueError, OSError):
            # Soft failure — mark unknown rather than broken
            repo.broken_homepage = None
            warnings.append(
                CollectionWarning(
                    code="homepage_check_failed",
                    message=f"Could not verify homepage: {repo.homepage}",
                    repository=repo.full_name,
                )
            )

    targets = [r for r in repositories if r.homepage and not r.archived][:40]
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(check, targets))


def _search_items(query: str, *, warnings: list[CollectionWarning], code: str) -> list[dict[str, Any]]:
    try:
        data = gh.api(
            f"/search/issues?q={_url_quote(query)}&per_page=50&sort=updated"
        )
    except gh.GhError as exc:
        warnings.append(CollectionWarning(code=code, message=str(exc)))
        return []
    if not isinstance(data, dict):
        return []
    items = data.get("items") or []
    return [i for i in items if isinstance(i, dict)]


def _url_quote(value: str) -> str:
    from urllib.parse import quote

    return quote(value, safe="")


def _repo_from_url(url: str | None) -> str:
    if not url:
        return "unknown"
    # https://api.github.com/repos/owner/name
    parts = url.rstrip("/").split("/")
    if len(parts) >= 2:
        return f"{parts[-2]}/{parts[-1]}"
    return "unknown"


def _collect_attention_items(
    login: str,
    *,
    warnings: list[CollectionWarning],
) -> tuple[list[PullRequestSummary], list[IssueSummary]]:
    prs: list[PullRequestSummary] = []
    issues: list[IssueSummary] = []

    review_items = _search_items(
        f"is:pr is:open review-requested:{login}",
        warnings=warnings,
        code="search_review_requests_failed",
    )
    own_pr_items = _search_items(
        f"is:pr is:open author:{login}",
        warnings=warnings,
        code="search_own_prs_failed",
    )
    assigned_items = _search_items(
        f"is:issue is:open assignee:{login}",
        warnings=warnings,
        code="search_assigned_issues_failed",
    )

    seen_prs: set[str] = set()
    for item in review_items + own_pr_items:
        key = item.get("html_url") or f"{item.get('id')}"
        if key in seen_prs:
            continue
        seen_prs.add(key)
        labels = [lbl.get("name") for lbl in (item.get("labels") or []) if isinstance(lbl, dict)]
        repo = _repo_from_url(item.get("repository_url"))
        is_review = item in review_items
        prs.append(
            PullRequestSummary(
                number=int(item.get("number") or 0),
                title=item.get("title") or "(no title)",
                repository=repo,
                state=item.get("state") or "open",
                draft=bool(item.get("draft")),
                html_url=item.get("html_url"),
                author=((item.get("user") or {}).get("login")),
                created_at=item.get("created_at"),
                updated_at=item.get("updated_at"),
                is_review_request=is_review,
                is_own=item in own_pr_items,
                labels=[x for x in labels if x],
            )
        )

    for item in assigned_items:
        labels = [lbl.get("name") for lbl in (item.get("labels") or []) if isinstance(lbl, dict)]
        issues.append(
            IssueSummary(
                number=int(item.get("number") or 0),
                title=item.get("title") or "(no title)",
                repository=_repo_from_url(item.get("repository_url")),
                state=item.get("state") or "open",
                html_url=item.get("html_url"),
                author=((item.get("user") or {}).get("login")),
                created_at=item.get("created_at"),
                updated_at=item.get("updated_at"),
                is_assigned=True,
                labels=[x for x in labels if x],
            )
        )
    return prs, issues


def _collect_activity(
    login: str,
    *,
    pages: int,
    warnings: list[CollectionWarning],
) -> list[ActivityEvent]:
    events: list[ActivityEvent] = []
    for page in range(1, pages + 1):
        try:
            raw = gh.api(f"/users/{login}/events?per_page=100&page={page}")
        except gh.GhError as exc:
            warnings.append(CollectionWarning(code="activity_failed", message=str(exc)))
            break
        if not isinstance(raw, list) or not raw:
            break
        for item in raw:
            if not isinstance(item, dict):
                continue
            events.append(_normalize_event(item))
    return events


def _normalize_event(item: dict[str, Any]) -> ActivityEvent:
    etype = item.get("type") or "Event"
    repo = (item.get("repo") or {}).get("name")
    created = item.get("created_at")
    payload = item.get("payload") or {}
    summary = etype
    url = None

    if etype == "PushEvent":
        count = payload.get("size") or len(payload.get("commits") or [])
        ref = (payload.get("ref") or "").replace("refs/heads/", "")
        summary = f"Pushed {count} commit(s) to {ref or 'a branch'}"
    elif etype == "PullRequestEvent":
        action = payload.get("action")
        pr = payload.get("pull_request") or {}
        summary = f"{(action or 'updated').capitalize()} pull request #{pr.get('number')}: {pr.get('title') or ''}".strip()
        url = pr.get("html_url")
    elif etype == "IssuesEvent":
        action = payload.get("action")
        issue = payload.get("issue") or {}
        summary = f"{(action or 'updated').capitalize()} issue #{issue.get('number')}: {issue.get('title') or ''}".strip()
        url = issue.get("html_url")
    elif etype == "CreateEvent":
        summary = f"Created {payload.get('ref_type') or 'ref'} {payload.get('ref') or ''}".strip()
    elif etype == "ReleaseEvent":
        release = payload.get("release") or {}
        summary = f"Published release {release.get('tag_name') or ''}".strip()
        url = release.get("html_url")
    elif etype == "WatchEvent":
        summary = "Starred a repository"
    elif etype == "ForkEvent":
        summary = "Forked a repository"
    elif etype == "IssueCommentEvent":
        issue = payload.get("issue") or {}
        summary = f"Commented on issue #{issue.get('number')}"
        url = (payload.get("comment") or {}).get("html_url")
    elif etype == "PullRequestReviewEvent":
        pr = payload.get("pull_request") or {}
        summary = f"Reviewed pull request #{pr.get('number')}"
    else:
        summary = etype.replace("Event", "")

    return ActivityEvent(
        type=_friendly_event_type(etype),
        repository=repo,
        created_at=created,
        summary=summary,
        url=url,
        raw_type=etype,
    )


def _friendly_event_type(etype: str) -> str:
    mapping = {
        "PushEvent": "push",
        "PullRequestEvent": "pull_request",
        "IssuesEvent": "issue",
        "CreateEvent": "create",
        "DeleteEvent": "delete",
        "ReleaseEvent": "release",
        "WatchEvent": "star",
        "ForkEvent": "fork",
        "IssueCommentEvent": "comment",
        "PullRequestReviewEvent": "review",
        "PullRequestReviewCommentEvent": "review_comment",
        "PublicEvent": "public",
        "MemberEvent": "member",
        "GollumEvent": "wiki",
    }
    return mapping.get(etype, etype)


def default_progress(message: str) -> None:
    print(message, file=sys.stderr)
