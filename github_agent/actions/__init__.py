"""Safe action proposals for low-risk GitHub metadata changes."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from github_agent import gh
from github_agent.models.findings import Finding


@dataclass
class ActionProposal:
    id: str
    action: str
    risk: str
    title: str
    description: str
    repository: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)
    reversible: bool = True
    requires_approval: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ActionResult:
    proposal_id: str
    ok: bool
    message: str
    dry_run: bool = True
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


FORBIDDEN_ACTIONS = {
    "delete_repo",
    "force_push",
    "rewrite_history",
    "change_visibility",
    "archive_repo_silent",
}


def proposals_from_findings(findings: list[Finding]) -> list[ActionProposal]:
    proposals: list[ActionProposal] = []
    for finding in findings:
        proposal = proposal_from_finding(finding)
        if proposal:
            proposals.append(proposal)
    return proposals


def proposal_from_finding(finding: Finding) -> ActionProposal | None:
    action = finding.recommended_action
    if not action or action in FORBIDDEN_ACTIONS:
        return None
    if finding.risk not in {"low", "read_only"}:
        # Content / significant changes need explicit skill-driven branch+PR flows
        if action in {"add_readme", "add_profile_readme", "consider_license"}:
            return ActionProposal(
                id=f"propose:{finding.id}",
                action=action,
                risk=finding.risk,
                title=finding.title,
                description=(
                    "This change touches repository content or policy. "
                    "Use a branch, show a diff, get approval, then open a pull request. "
                    "This CLI will not apply it automatically."
                ),
                repository=finding.repository,
                payload={"finding_id": finding.id, "evidence": finding.evidence},
                reversible=True,
                requires_approval=True,
            )
        return None

    if action == "add_description":
        return ActionProposal(
            id=f"propose:{finding.id}",
            action="update_description",
            risk="low",
            title=f"Add description for {finding.repository}",
            description="Set a repository description after you provide/approve the text.",
            repository=finding.repository,
            payload={
                "finding_id": finding.id,
                "field": "description",
                "current": finding.evidence.get("description"),
                "proposed": None,
            },
        )
    if action == "add_topics":
        return ActionProposal(
            id=f"propose:{finding.id}",
            action="update_topics",
            risk="low",
            title=f"Add topics for {finding.repository}",
            description="Set repository topics after you approve the list.",
            repository=finding.repository,
            payload={
                "finding_id": finding.id,
                "field": "topics",
                "current": finding.evidence.get("topics"),
                "proposed": None,
            },
        )
    if action in {"add_homepage", "fix_homepage"}:
        return ActionProposal(
            id=f"propose:{finding.id}",
            action="update_homepage",
            risk="low",
            title=f"Update homepage for {finding.repository}",
            description="Set or fix the homepage URL after approval.",
            repository=finding.repository,
            payload={
                "finding_id": finding.id,
                "field": "homepage",
                "current": finding.evidence.get("homepage"),
                "proposed": finding.evidence.get("suggested"),
            },
        )
    if action == "complete_profile":
        return ActionProposal(
            id=f"propose:{finding.id}",
            action="update_profile",
            risk="low",
            title="Update GitHub profile fields",
            description="Preview profile field updates and apply only with approval.",
            payload={
                "finding_id": finding.id,
                "missing_fields": finding.evidence.get("missing_fields"),
            },
        )
    return None


def apply_metadata_update(
    *,
    owner: str,
    repo: str,
    description: str | None = None,
    homepage: str | None = None,
    dry_run: bool = True,
) -> ActionResult:
    payload: dict[str, Any] = {}
    if description is not None:
        payload["description"] = description
    if homepage is not None:
        payload["homepage"] = homepage
    if not payload:
        return ActionResult(
            proposal_id=f"{owner}/{repo}",
            ok=False,
            message="No metadata fields provided.",
            dry_run=dry_run,
        )
    if dry_run:
        return ActionResult(
            proposal_id=f"{owner}/{repo}",
            ok=True,
            message="Dry run only — no remote changes made.",
            dry_run=True,
            details={"would_patch": payload, "endpoint": f"/repos/{owner}/{repo}"},
        )
    gh.api(f"/repos/{owner}/{repo}", method="PATCH", input_json=payload)
    return ActionResult(
        proposal_id=f"{owner}/{repo}",
        ok=True,
        message="Repository metadata updated.",
        dry_run=False,
        details={"patched": payload},
    )


def apply_topics_update(
    *,
    owner: str,
    repo: str,
    topics: list[str],
    dry_run: bool = True,
) -> ActionResult:
    cleaned = [t.strip().lower().replace(" ", "-") for t in topics if t and t.strip()]
    if dry_run:
        return ActionResult(
            proposal_id=f"{owner}/{repo}:topics",
            ok=True,
            message="Dry run only — no remote changes made.",
            dry_run=True,
            details={"would_put_topics": cleaned},
        )
    gh.api(
        f"/repos/{owner}/{repo}/topics",
        method="PUT",
        input_json={"names": cleaned},
    )
    return ActionResult(
        proposal_id=f"{owner}/{repo}:topics",
        ok=True,
        message="Repository topics updated.",
        dry_run=False,
        details={"topics": cleaned},
    )
