"""Normalized account snapshot and related models."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


@dataclass
class Profile:
    login: str
    name: str | None = None
    bio: str | None = None
    company: str | None = None
    location: str | None = None
    blog: str | None = None
    twitter_username: str | None = None
    email: str | None = None
    avatar_url: str | None = None
    html_url: str | None = None
    public_repos: int = 0
    public_gists: int = 0
    followers: int = 0
    following: int = 0
    created_at: str | None = None
    updated_at: str | None = None
    hireable: bool | None = None
    profile_readme: bool | None = None
    profile_readme_preview: str | None = None

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> Profile:
        return cls(
            login=data.get("login") or "",
            name=data.get("name"),
            bio=data.get("bio"),
            company=data.get("company"),
            location=data.get("location"),
            blog=data.get("blog") or None,
            twitter_username=data.get("twitter_username"),
            email=data.get("email"),
            avatar_url=data.get("avatar_url"),
            html_url=data.get("html_url"),
            public_repos=int(data.get("public_repos") or 0),
            public_gists=int(data.get("public_gists") or 0),
            followers=int(data.get("followers") or 0),
            following=int(data.get("following") or 0),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
            hireable=data.get("hireable"),
        )


@dataclass
class Repository:
    name: str
    full_name: str
    private: bool = False
    fork: bool = False
    archived: bool = False
    disabled: bool = False
    description: str | None = None
    homepage: str | None = None
    html_url: str | None = None
    language: str | None = None
    topics: list[str] = field(default_factory=list)
    license_spdx: str | None = None
    default_branch: str | None = None
    size: int = 0
    stargazers_count: int = 0
    forks_count: int = 0
    open_issues_count: int = 0
    has_issues: bool = True
    has_wiki: bool = False
    has_pages: bool = False
    is_template: bool = False
    pushed_at: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    visibility: str | None = None
    parent_full_name: str | None = None
    # Level-2 enrichment (optional)
    has_readme: bool | None = None
    readme_preview: str | None = None
    workflow_conclusion: str | None = None
    workflow_name: str | None = None
    broken_homepage: bool | None = None

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> Repository:
        license_info = data.get("license") or {}
        parent = data.get("parent") or {}
        topics = data.get("topics") or []
        return cls(
            name=data.get("name") or "",
            full_name=data.get("full_name") or "",
            private=bool(data.get("private")),
            fork=bool(data.get("fork")),
            archived=bool(data.get("archived")),
            disabled=bool(data.get("disabled")),
            description=(data.get("description") or None),
            homepage=(data.get("homepage") or None) or None,
            html_url=data.get("html_url"),
            language=data.get("language"),
            topics=list(topics),
            license_spdx=(license_info.get("spdx_id") if isinstance(license_info, dict) else None),
            default_branch=data.get("default_branch"),
            size=int(data.get("size") or 0),
            stargazers_count=int(data.get("stargazers_count") or 0),
            forks_count=int(data.get("forks_count") or 0),
            open_issues_count=int(data.get("open_issues_count") or 0),
            has_issues=bool(data.get("has_issues", True)),
            has_wiki=bool(data.get("has_wiki")),
            has_pages=bool(data.get("has_pages")),
            is_template=bool(data.get("is_template")),
            pushed_at=data.get("pushed_at"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
            visibility=data.get("visibility"),
            parent_full_name=parent.get("full_name") if isinstance(parent, dict) else None,
        )


@dataclass
class PullRequestSummary:
    number: int
    title: str
    repository: str
    state: str
    draft: bool = False
    html_url: str | None = None
    author: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    is_review_request: bool = False
    is_own: bool = False
    labels: list[str] = field(default_factory=list)


@dataclass
class IssueSummary:
    number: int
    title: str
    repository: str
    state: str
    html_url: str | None = None
    author: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    is_assigned: bool = False
    labels: list[str] = field(default_factory=list)


@dataclass
class WorkflowRunSummary:
    repository: str
    name: str
    conclusion: str | None
    status: str | None
    html_url: str | None = None
    head_branch: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


@dataclass
class ActivityEvent:
    type: str
    repository: str | None
    created_at: str | None
    summary: str
    url: str | None = None
    raw_type: str | None = None


@dataclass
class CollectionWarning:
    code: str
    message: str
    repository: str | None = None


@dataclass
class AccountSnapshot:
    collected_at: str
    viewer_login: str
    profile: Profile
    repositories: list[Repository] = field(default_factory=list)
    pull_requests: list[PullRequestSummary] = field(default_factory=list)
    issues: list[IssueSummary] = field(default_factory=list)
    workflow_runs: list[WorkflowRunSummary] = field(default_factory=list)
    activity: list[ActivityEvent] = field(default_factory=list)
    warnings: list[CollectionWarning] = field(default_factory=list)
    meta: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AccountSnapshot:
        profile = Profile(**_filter_fields(Profile, data["profile"]))
        repos = [Repository(**_filter_fields(Repository, r)) for r in data.get("repositories", [])]
        prs = [
            PullRequestSummary(**_filter_fields(PullRequestSummary, p))
            for p in data.get("pull_requests", [])
        ]
        issues = [IssueSummary(**_filter_fields(IssueSummary, i)) for i in data.get("issues", [])]
        workflows = [
            WorkflowRunSummary(**_filter_fields(WorkflowRunSummary, w))
            for w in data.get("workflow_runs", [])
        ]
        activity = [
            ActivityEvent(**_filter_fields(ActivityEvent, a)) for a in data.get("activity", [])
        ]
        warnings = [
            CollectionWarning(**_filter_fields(CollectionWarning, w))
            for w in data.get("warnings", [])
        ]
        return cls(
            collected_at=data["collected_at"],
            viewer_login=data["viewer_login"],
            profile=profile,
            repositories=repos,
            pull_requests=prs,
            issues=issues,
            workflow_runs=workflows,
            activity=activity,
            warnings=warnings,
            meta=dict(data.get("meta") or {}),
        )


def _filter_fields(cls: type, data: dict[str, Any]) -> dict[str, Any]:
    import dataclasses

    names = {f.name for f in dataclasses.fields(cls)}
    return {k: v for k, v in data.items() if k in names}


def parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def days_since(value: str | None, *, now: datetime | None = None) -> int | None:
    dt = parse_iso(value)
    if dt is None:
        return None
    current = now or datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return max(0, (current - dt).days)
