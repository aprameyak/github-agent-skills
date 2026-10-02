"""Normalized Finding model and risk vocabulary."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

Severity = Literal["info", "suggestion", "attention", "urgent"]
Confidence = Literal["low", "medium", "high"]
Risk = Literal["read_only", "low", "medium", "high", "forbidden"]
Category = Literal[
    "profile",
    "presentation",
    "cleanup",
    "documentation",
    "attention",
    "security",
    "activity",
    "consistency",
    "other",
]


@dataclass
class Finding:
    id: str
    category: Category
    severity: Severity
    confidence: Confidence
    title: str
    explanation: str
    evidence: dict[str, Any] = field(default_factory=dict)
    recommended_action: str | None = None
    risk: Risk = "read_only"
    repository: str | None = None
    heuristic: bool = False
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Finding:
        return cls(
            id=data["id"],
            category=data["category"],
            severity=data["severity"],
            confidence=data["confidence"],
            title=data["title"],
            explanation=data["explanation"],
            evidence=dict(data.get("evidence") or {}),
            recommended_action=data.get("recommended_action"),
            risk=data.get("risk") or "read_only",
            repository=data.get("repository"),
            heuristic=bool(data.get("heuristic", False)),
            tags=list(data.get("tags") or []),
        )


@dataclass
class FindingsReport:
    generated_at: str
    viewer_login: str
    skill: str
    findings: list[Finding] = field(default_factory=list)
    summary: dict[str, Any] = field(default_factory=dict)
    meta: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "generated_at": self.generated_at,
            "viewer_login": self.viewer_login,
            "skill": self.skill,
            "findings": [f.to_dict() for f in self.findings],
            "summary": self.summary,
            "meta": self.meta,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FindingsReport:
        return cls(
            generated_at=data["generated_at"],
            viewer_login=data["viewer_login"],
            skill=data["skill"],
            findings=[Finding.from_dict(f) for f in data.get("findings", [])],
            summary=dict(data.get("summary") or {}),
            meta=dict(data.get("meta") or {}),
        )


SEVERITY_ORDER = {"urgent": 0, "attention": 1, "suggestion": 2, "info": 3}
RISK_ORDER = {"read_only": 0, "low": 1, "medium": 2, "high": 3, "forbidden": 4}


def sort_findings(findings: list[Finding]) -> list[Finding]:
    return sorted(
        findings,
        key=lambda f: (
            SEVERITY_ORDER.get(f.severity, 9),
            RISK_ORDER.get(f.risk, 9),
            0 if f.confidence == "high" else 1 if f.confidence == "medium" else 2,
            f.repository or "",
            f.id,
        ),
    )


def group_counts(findings: list[Finding]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for finding in findings:
        counts[finding.category] = counts.get(finding.category, 0) + 1
    return counts
