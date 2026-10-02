"""Model and risk classification tests."""

from __future__ import annotations

from github_agent.actions import apply_metadata_update
from github_agent.models.account import Repository, days_since, utc_now_iso
from github_agent.models.findings import Finding, FindingsReport, group_counts


def test_finding_roundtrip():
    f = Finding(
        id="missing-description:demo",
        category="presentation",
        severity="suggestion",
        confidence="high",
        title="Repository has no description",
        explanation="Add one",
        evidence={"description": None},
        recommended_action="add_description",
        risk="low",
        repository="demo",
    )
    restored = Finding.from_dict(f.to_dict())
    assert restored.id == f.id
    assert restored.evidence["description"] is None


def test_group_counts():
    findings = [
        Finding(
            id="1",
            category="presentation",
            severity="suggestion",
            confidence="high",
            title="t",
            explanation="e",
        ),
        Finding(
            id="2",
            category="presentation",
            severity="suggestion",
            confidence="high",
            title="t",
            explanation="e",
        ),
        Finding(
            id="3",
            category="cleanup",
            severity="info",
            confidence="medium",
            title="t",
            explanation="e",
        ),
    ]
    assert group_counts(findings) == {"presentation": 2, "cleanup": 1}


def test_days_since():
    assert days_since(None) is None
    assert days_since("2026-09-01T00:00:00Z", now=__import__("datetime").datetime(2026, 9, 29, tzinfo=__import__("datetime").timezone.utc)) == 28


def test_repo_from_api_like_dict():
    repo = Repository.from_api(
        {
            "name": "demo",
            "full_name": "me/demo",
            "private": False,
            "fork": False,
            "archived": False,
            "description": "x",
            "homepage": "",
            "topics": ["cli"],
            "license": {"spdx_id": "MIT"},
            "size": 10,
            "stargazers_count": 1,
            "forks_count": 0,
            "open_issues_count": 0,
            "owner": {"login": "me"},
        }
    )
    assert repo.homepage is None
    assert repo.license_spdx == "MIT"
    assert repo.topics == ["cli"]


def test_apply_metadata_dry_run_only():
    result = apply_metadata_update(
        owner="me",
        repo="demo",
        description="Hello",
        dry_run=True,
    )
    assert result.ok
    assert result.dry_run
    assert result.details["would_patch"]["description"] == "Hello"


def test_report_to_dict():
    report = FindingsReport(
        generated_at=utc_now_iso(),
        viewer_login="me",
        skill="github-checkup",
        findings=[],
        summary={"finding_count": 0},
    )
    assert report.to_dict()["viewer_login"] == "me"
