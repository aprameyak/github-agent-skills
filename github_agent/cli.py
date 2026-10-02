"""Internal CLI for humans and coding agents."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from github_agent import __version__, gh
from github_agent.actions import (
    apply_metadata_update,
    apply_topics_update,
    proposals_from_findings,
)
from github_agent.analyzers import analyze, build_recap
from github_agent.collectors import collect_snapshot, default_progress
from github_agent.models.account import AccountSnapshot
from github_agent.reporting import (
    format_auth,
    format_checkup,
    format_cleanup,
    format_fix,
    format_polish,
    format_recap,
    format_snapshot_brief,
    format_today,
    print_json,
)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except gh.GhError as exc:
        print(f"error: {exc}", file=sys.stderr)
        if exc.stderr:
            print(exc.stderr, file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("Interrupted.", file=sys.stderr)
        return 130


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="github-agent",
        description="Inspect and tidy a GitHub account using your existing gh auth.",
    )
    parser.add_argument("--version", action="version", version=f"github-agent {__version__}")

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON where applicable.",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    p_auth = sub.add_parser("auth-check", parents=[common], help="Verify gh authentication.")
    p_auth.set_defaults(func=cmd_auth_check)

    p_snap = sub.add_parser(
        "snapshot", parents=[common], help="Collect a normalized account snapshot."
    )
    p_snap.add_argument("--out", type=Path, help="Write snapshot JSON to this path.")
    p_snap.add_argument("--user", help="GitHub username (defaults to authenticated user).")
    p_snap.add_argument("--no-readmes", action="store_true", help="Skip README enrichment.")
    p_snap.add_argument("--no-workflows", action="store_true", help="Skip workflow checks.")
    p_snap.add_argument("--check-homepages", action="store_true", help="Probe homepage URLs.")
    p_snap.add_argument("--quiet", action="store_true", help="Suppress progress on stderr.")
    p_snap.set_defaults(func=cmd_snapshot)

    p_analyze = sub.add_parser(
        "analyze", parents=[common], help="Analyze a snapshot and emit findings."
    )
    p_analyze.add_argument(
        "--snapshot",
        type=Path,
        help="Snapshot JSON path. If omitted, collect a fresh snapshot.",
    )
    p_analyze.add_argument(
        "--skill",
        default="github-checkup",
        choices=[
            "github-checkup",
            "github-cleanup",
            "github-polish",
            "github-fix",
            "github-today",
            "all",
        ],
        help="Which skill lens to apply.",
    )
    p_analyze.add_argument("--out", type=Path, help="Write findings JSON to this path.")
    p_analyze.add_argument("--quiet", action="store_true")
    p_analyze.set_defaults(func=cmd_analyze)

    p_findings = sub.add_parser(
        "findings", parents=[common], help="Alias for analyze with JSON default."
    )
    p_findings.add_argument("--snapshot", type=Path)
    p_findings.add_argument(
        "--skill",
        default="all",
        choices=[
            "github-checkup",
            "github-cleanup",
            "github-polish",
            "github-fix",
            "github-today",
            "all",
        ],
    )
    p_findings.add_argument("--out", type=Path)
    p_findings.add_argument("--quiet", action="store_true")
    p_findings.set_defaults(func=cmd_findings)

    p_today = sub.add_parser("today", parents=[common], help="What needs attention on GitHub.")
    p_today.add_argument("--snapshot", type=Path)
    p_today.add_argument("--quiet", action="store_true")
    p_today.set_defaults(func=cmd_today)

    p_recap = sub.add_parser("recap", parents=[common], help="Summarize recent GitHub activity.")
    p_recap.add_argument("--snapshot", type=Path)
    p_recap.add_argument(
        "--since",
        default="30d",
        help="Time window: 7d, 30d, 90d, or year.",
    )
    p_recap.add_argument("--quiet", action="store_true")
    p_recap.set_defaults(func=cmd_recap)

    p_checkup = sub.add_parser("checkup", parents=[common], help="Friendly account checkup.")
    p_checkup.add_argument("--snapshot", type=Path)
    p_checkup.add_argument("--quiet", action="store_true")
    p_checkup.set_defaults(func=cmd_checkup)

    p_cleanup = sub.add_parser(
        "cleanup", parents=[common], help="Conservative cleanup candidates."
    )
    p_cleanup.add_argument("--snapshot", type=Path)
    p_cleanup.add_argument("--quiet", action="store_true")
    p_cleanup.set_defaults(func=cmd_cleanup)

    p_polish = sub.add_parser("polish", parents=[common], help="Presentation improvements.")
    p_polish.add_argument("--snapshot", type=Path)
    p_polish.add_argument("--quiet", action="store_true")
    p_polish.set_defaults(func=cmd_polish)

    p_fix = sub.add_parser("fix", parents=[common], help="Low-risk safe fix proposals.")
    p_fix.add_argument("--snapshot", type=Path)
    p_fix.add_argument("--quiet", action="store_true")
    p_fix.set_defaults(func=cmd_fix)

    p_propose = sub.add_parser(
        "propose",
        parents=[common],
        help="Build approval-required action proposals from findings JSON.",
    )
    p_propose.add_argument("findings", type=Path, help="Findings JSON from analyze/findings.")
    p_propose.add_argument("--out", type=Path)
    p_propose.set_defaults(func=cmd_propose)

    p_apply = sub.add_parser(
        "apply-metadata",
        parents=[common],
        help="Apply an approved low-risk repository metadata change.",
    )
    p_apply.add_argument("--repo", required=True, help="owner/name")
    p_apply.add_argument("--description")
    p_apply.add_argument("--homepage")
    p_apply.add_argument("--topics", help="Comma-separated topics.")
    p_apply.add_argument(
        "--execute",
        action="store_true",
        help="Actually mutate GitHub. Without this flag, dry-run only.",
    )
    p_apply.set_defaults(func=cmd_apply_metadata)

    return parser


def cmd_auth_check(args: argparse.Namespace) -> int:
    status = gh.auth_status()
    if getattr(args, "json", False):
        print_json(
            {
                "logged_in": status.logged_in,
                "host": status.host,
                "username": status.username,
                "protocol": status.protocol,
                "scopes": status.scopes,
            },
            stream=sys.stdout,
        )
    else:
        sys.stdout.write(format_auth(status))
    return 0 if status.logged_in else 1


def cmd_snapshot(args: argparse.Namespace) -> int:
    snapshot = _load_or_collect(args)
    data = snapshot.to_dict()
    if args.out:
        args.out.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        if not args.json:
            print(f"Wrote snapshot to {args.out}", file=sys.stderr)
    if args.json or not args.out:
        if args.json:
            print_json(data, stream=sys.stdout)
        else:
            sys.stdout.write(format_snapshot_brief(snapshot))
            if not args.out:
                print(
                    "Tip: pass --out snapshot.json or --json for the full snapshot.",
                    file=sys.stderr,
                )
    return 0


def cmd_analyze(args: argparse.Namespace) -> int:
    snapshot = _load_or_collect(args)
    report = analyze(snapshot, skill=args.skill)
    data = report.to_dict()
    if args.out:
        args.out.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    if args.json:
        print_json(data, stream=sys.stdout)
    else:
        sys.stdout.write(_human_for_skill(args.skill, report, snapshot))
    return 0


def cmd_findings(args: argparse.Namespace) -> int:
    args.json = True
    return cmd_analyze(args)


def cmd_today(args: argparse.Namespace) -> int:
    snapshot = _load_or_collect(args)
    report = analyze(snapshot, skill="github-today")
    if args.json:
        print_json(report.to_dict(), stream=sys.stdout)
    else:
        sys.stdout.write(format_today(report))
    return 0


def cmd_checkup(args: argparse.Namespace) -> int:
    snapshot = _load_or_collect(args)
    report = analyze(snapshot, skill="github-checkup")
    if args.json:
        print_json(report.to_dict(), stream=sys.stdout)
    else:
        sys.stdout.write(format_checkup(report, snapshot))
    return 0


def cmd_cleanup(args: argparse.Namespace) -> int:
    snapshot = _load_or_collect(args)
    report = analyze(snapshot, skill="github-cleanup")
    if args.json:
        print_json(report.to_dict(), stream=sys.stdout)
    else:
        sys.stdout.write(format_cleanup(report))
    return 0


def cmd_polish(args: argparse.Namespace) -> int:
    snapshot = _load_or_collect(args)
    report = analyze(snapshot, skill="github-polish")
    if args.json:
        print_json(report.to_dict(), stream=sys.stdout)
    else:
        sys.stdout.write(format_polish(report))
    return 0


def cmd_fix(args: argparse.Namespace) -> int:
    snapshot = _load_or_collect(args)
    report = analyze(snapshot, skill="github-fix")
    if args.json:
        print_json(report.to_dict(), stream=sys.stdout)
    else:
        sys.stdout.write(format_fix(report))
    return 0


def cmd_recap(args: argparse.Namespace) -> int:
    snapshot = _load_or_collect(args)
    days = parse_since(args.since)
    recap = build_recap(snapshot, since_days=days)
    if args.json:
        print_json(recap, stream=sys.stdout)
    else:
        sys.stdout.write(format_recap(recap))
    return 0


def cmd_propose(args: argparse.Namespace) -> int:
    data = json.loads(args.findings.read_text(encoding="utf-8"))
    from github_agent.models.findings import FindingsReport

    report = FindingsReport.from_dict(data)
    proposals = [p.to_dict() for p in proposals_from_findings(report.findings)]
    payload = {"count": len(proposals), "proposals": proposals}
    if args.out:
        args.out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print_json(payload, stream=sys.stdout)
    return 0


def cmd_apply_metadata(args: argparse.Namespace) -> int:
    if "/" not in args.repo:
        print("error: --repo must look like owner/name", file=sys.stderr)
        return 2
    owner, name = args.repo.split("/", 1)
    dry_run = not args.execute
    results = []
    if args.description is not None or args.homepage is not None:
        results.append(
            apply_metadata_update(
                owner=owner,
                repo=name,
                description=args.description,
                homepage=args.homepage,
                dry_run=dry_run,
            ).to_dict()
        )
    if args.topics is not None:
        topics = [t.strip() for t in args.topics.split(",") if t.strip()]
        results.append(
            apply_topics_update(
                owner=owner,
                repo=name,
                topics=topics,
                dry_run=dry_run,
            ).to_dict()
        )
    if not results:
        print("error: provide --description, --homepage, and/or --topics", file=sys.stderr)
        return 2
    print_json({"dry_run": dry_run, "results": results}, stream=sys.stdout)
    return 0


def _load_or_collect(args: argparse.Namespace) -> AccountSnapshot:
    snapshot_path = getattr(args, "snapshot", None)
    if snapshot_path:
        data = json.loads(Path(snapshot_path).read_text(encoding="utf-8"))
        return AccountSnapshot.from_dict(data)

    quiet = getattr(args, "quiet", False)
    progress = None if quiet else default_progress
    return collect_snapshot(
        username=getattr(args, "user", None),
        enrich_readmes=not getattr(args, "no_readmes", False),
        enrich_workflows=not getattr(args, "no_workflows", False),
        check_homepages=getattr(args, "check_homepages", False),
        progress=progress,
    )


def _human_for_skill(skill: str, report: Any, snapshot: AccountSnapshot) -> str:
    if skill == "github-cleanup":
        return format_cleanup(report)
    if skill == "github-polish":
        return format_polish(report)
    if skill == "github-fix":
        return format_fix(report)
    if skill == "github-today":
        return format_today(report)
    return format_checkup(report, snapshot)


def parse_since(value: str) -> int:
    text = value.strip().lower()
    if text in {"year", "1y", "365d"}:
        return 365
    if text.endswith("d") and text[:-1].isdigit():
        return int(text[:-1])
    if text.isdigit():
        return int(text)
    raise SystemExit(f"Unrecognized --since value: {value} (try 7d, 30d, 90d, year)")


if __name__ == "__main__":
    raise SystemExit(main())
