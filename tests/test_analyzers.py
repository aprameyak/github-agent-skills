"""Analyzer unit tests using fixtures."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from github_agent.analyzers import analyze, build_recap
from github_agent.models.account import AccountSnapshot
from github_agent.models.findings import Finding, sort_findings
from github_agent.actions import proposal_from_finding, FORBIDDEN_ACTIONS

FIX = Path(__file__).resolve().parent / "fixtures"
NOW = datetime(2026, 9, 29, tzinfo=timezone.utc)


def load(name: str) -> AccountSnapshot:
    return AccountSnapshot.from_dict(json.loads((FIX / name).read_text()))


def test_new_user_checkup_finds_profile_and_presentation_gaps():
    report = analyze(load("new_user.json"), skill="github-checkup", now=NOW)
    ids = {f.id for f in report.findings}
    assert "profile:incomplete" in ids
    assert "profile:missing-readme" in ids
    assert any(f.id.startswith("missing-description:") for f in report.findings)
    assert report.summary["repository_count"] == 3


def test_student_cleanup_flags_empty_and_version_groups():
    report = analyze(load("student.json"), skill="github-cleanup", now=NOW)
    ids = {f.id for f in report.findings}
    assert "empty-repo:empty-idea" in ids
    assert any(f.id.startswith("versioned-group:") for f in report.findings)
    assert any(f.id.startswith("stale-repo:") for f in report.findings)
    # Never recommend deletion
    assert all(f.recommended_action != "delete_repo" for f in report.findings)


def test_professional_today_prioritizes_attention():
    report = analyze(load("professional.json"), skill="github-today", now=NOW)
    assert report.findings
    assert any(f.category == "attention" for f in report.findings)
    assert any("review-request:" in f.id for f in report.findings)
    assert any("failed-workflow:" in f.id for f in report.findings)


def test_fix_skill_only_low_risk_non_heuristic():
    report = analyze(load("professional.json"), skill="github-fix", now=NOW)
    assert report.findings
    for f in report.findings:
        assert f.risk in {"read_only", "low"}
        assert f.confidence != "low"
        assert not f.heuristic
        assert f.recommended_action in {
            "add_description",
            "add_topics",
            "add_homepage",
            "fix_homepage",
            "complete_profile",
        }


def test_maintainer_scale_does_not_explode():
    report = analyze(load("maintainer.json"), skill="github-checkup", now=NOW)
    assert report.summary["repository_count"] == 80
    assert isinstance(report.findings, list)


def test_edge_empty_account():
    report = analyze(load("edge_empty.json"), skill="github-checkup", now=NOW)
    assert any(f.id.startswith("profile:") for f in report.findings)


def test_edge_forks_only():
    report = analyze(load("edge_forks_only.json"), skill="github-cleanup", now=NOW)
    assert any("old-fork:" in f.id for f in report.findings)


def test_edge_archived():
    report = analyze(load("edge_archived.json"), skill="github-cleanup", now=NOW)
    assert any(f.id == "archived:many-visible" for f in report.findings)


def test_missing_readme_finding():
    report = analyze(load("edge_missing_readme.json"), skill="github-polish", now=NOW)
    assert any(f.id == "missing-readme:bare" for f in report.findings)


def test_recap_facts_are_evidence_backed():
    recap = build_recap(load("student.json"), since_days=30, now=NOW)
    assert recap["facts"]["pull_requests_opened"] >= 1
    assert recap["facts"]["commits_pushed_estimate"] >= 3
    assert recap["summary_lines"]
    assert "note" in recap["facts"]


def test_finding_sort_orders_severity():
    findings = [
        Finding(
            id="b",
            category="other",
            severity="suggestion",
            confidence="high",
            title="b",
            explanation="b",
            risk="low",
        ),
        Finding(
            id="a",
            category="attention",
            severity="attention",
            confidence="high",
            title="a",
            explanation="a",
            risk="read_only",
        ),
    ]
    ordered = sort_findings(findings)
    assert ordered[0].id == "a"


def test_proposal_skips_forbidden():
    finding = Finding(
        id="x",
        category="cleanup",
        severity="suggestion",
        confidence="high",
        title="x",
        explanation="x",
        recommended_action="delete_repo",
        risk="forbidden",
    )
    assert "delete_repo" in FORBIDDEN_ACTIONS
    assert proposal_from_finding(finding) is None


def test_snapshot_roundtrip():
    original = load("new_user.json")
    restored = AccountSnapshot.from_dict(original.to_dict())
    assert restored.viewer_login == original.viewer_login
    assert len(restored.repositories) == len(original.repositories)


def test_partial_permissions_preserve_warnings():
    snap = load("edge_partial_permissions.json")
    assert snap.warnings
    report = analyze(snap, skill="github-checkup", now=NOW)
    assert report.meta["warning_count"] == 1
