"""CLI behavior tests without hitting live GitHub."""

from __future__ import annotations

import json
from pathlib import Path

from github_agent.cli import main, parse_since

FIX = Path(__file__).resolve().parent / "fixtures"


def test_parse_since():
    assert parse_since("7d") == 7
    assert parse_since("30d") == 30
    assert parse_since("year") == 365
    assert parse_since("90") == 90


def test_checkup_from_fixture(capsys):
    code = main(["checkup", "--snapshot", str(FIX / "new_user.json")])
    assert code == 0
    out = capsys.readouterr().out
    assert "GitHub Checkup" in out
    assert "repositor" in out.lower()


def test_findings_json(capsys):
    code = main(
        [
            "findings",
            "--snapshot",
            str(FIX / "student.json"),
            "--skill",
            "github-cleanup",
        ]
    )
    assert code == 0
    data = json.loads(capsys.readouterr().out)
    assert data["skill"] == "github-cleanup"
    assert isinstance(data["findings"], list)


def test_today_and_recap(capsys):
    assert main(["today", "--snapshot", str(FIX / "professional.json")]) == 0
    out = capsys.readouterr().out
    assert "GitHub Today" in out

    assert main(["recap", "--snapshot", str(FIX / "student.json"), "--since", "30d", "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["since_days"] == 30


def test_propose_and_dry_run_apply(tmp_path, capsys):
    findings_path = tmp_path / "findings.json"
    assert (
        main(
            [
                "analyze",
                "--snapshot",
                str(FIX / "new_user.json"),
                "--skill",
                "github-fix",
                "--json",
                "--out",
                str(findings_path),
            ]
        )
        == 0
    )
    # clear analyze stdout
    capsys.readouterr()
    assert main(["propose", str(findings_path)]) == 0
    proposed = json.loads(capsys.readouterr().out)
    assert "proposals" in proposed

    assert (
        main(
            [
                "apply-metadata",
                "--repo",
                "newbie/hello-world",
                "--description",
                "A hello world experiment",
            ]
        )
        == 0
    )
    applied = json.loads(capsys.readouterr().out)
    assert applied["dry_run"] is True


def test_auth_check_json(monkeypatch, capsys):
    from github_agent import gh
    from github_agent.gh import AuthStatus

    monkeypatch.setattr(
        gh,
        "auth_status",
        lambda: AuthStatus(
            logged_in=True,
            host="github.com",
            username="tester",
            protocol="https",
            scopes=["repo"],
            message="ok",
        ),
    )
    assert main(["auth-check", "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["logged_in"] is True
    assert data["username"] == "tester"
