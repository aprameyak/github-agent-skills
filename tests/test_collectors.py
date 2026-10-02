"""Collector helper / pagination parsing tests."""

from __future__ import annotations

import json
from unittest.mock import patch

from github_agent.collectors import _normalize_event, _repo_from_url
from github_agent.gh import AuthStatus, _api_paginate


def test_repo_from_url():
    assert _repo_from_url("https://api.github.com/repos/acme/api") == "acme/api"
    assert _repo_from_url(None) == "unknown"


def test_normalize_push_event():
    event = _normalize_event(
        {
            "type": "PushEvent",
            "repo": {"name": "me/demo"},
            "created_at": "2026-09-20T00:00:00Z",
            "payload": {"size": 2, "ref": "refs/heads/main", "commits": [{}, {}]},
        }
    )
    assert event.type == "push"
    assert "Pushed 2" in event.summary
    assert event.repository == "me/demo"


def test_api_paginate_concatenated_arrays():
    class Result:
        stdout = json.dumps([{"id": 1}]) + "\n" + json.dumps([{"id": 2}])
        stderr = ""
        returncode = 0

    with patch("github_agent.gh.run_gh", return_value=Result()):
        items = _api_paginate("/user/repos")
    assert items == [{"id": 1}, {"id": 2}]


def test_auth_status_shape():
    status = AuthStatus(
        logged_in=False,
        host="github.com",
        username=None,
        protocol=None,
        scopes=[],
        message="no",
    )
    assert status.logged_in is False
