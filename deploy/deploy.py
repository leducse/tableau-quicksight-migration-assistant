#!/usr/bin/env python3
"""QuickSight deploy entrypoint.

Default behavior is a safe ``--dry-run`` that prints the ordered QuickSight API
plan and writes ``deploy/dry_run_plan.json``. Real QuickSight calls are NEVER
made in dry-run. ``--deploy-dev`` is guarded: it is off by default, requires an
approved migration report (``deploy_allowed: true``), boto3, and an explicit
``--i-understand`` acknowledgement.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.common import write_json  # noqa: E402
from src.deploy import build_plan  # noqa: E402


def _print_plan(plan: dict) -> None:
    print(f"QuickSight deploy plan for workbook: {plan['workbook_id']}")
    print("-" * 60)
    for i, action in enumerate(plan["ordered_actions"], start=1):
        resource = action.get("resource_id", "")
        print(f"{i:>2}. {action['action']:<18} {resource}")
        for key, value in action.items():
            if key in {"action", "resource_id"}:
                continue
            print(f"      {key}: {value}")
    print("-" * 60)
    print("Summary:")
    for action, count in plan["summary"].items():
        print(f"  {action}: {count}")


def _load_report(package_root: Path) -> dict | None:
    report_path = package_root / "validation" / "migration_report.json"
    if not report_path.exists():
        return None
    with open(report_path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="QuickSight migration deploy")
    parser.add_argument("--package", required=True, help="Path to migration package root")
    parser.add_argument("--dry-run", action="store_true", help="Print plan only; no AWS mutations (default)")
    parser.add_argument("--deploy-dev", action="store_true", help="GUARDED: apply to dev QuickSight account")
    parser.add_argument("--profile", default="dev", help="AWS profile for dev deploy")
    parser.add_argument("--i-understand", action="store_true", help="Required ack for --deploy-dev")
    args = parser.parse_args(argv)

    package_root = Path(args.package).resolve()
    plan = build_plan(package_root)

    plan_path = package_root / "deploy" / "dry_run_plan.json"
    write_json(plan_path, plan)

    if not args.deploy_dev:
        _print_plan(plan)
        print(f"\nDry-run plan written to: {plan_path}")
        print("No QuickSight resources were created (dry-run).")
        return 0

    # --- Guarded dev deploy path ---
    report = _load_report(package_root)
    if not report or not report.get("deploy_allowed"):
        print("Refusing --deploy-dev: migration report missing or deploy_allowed is false.")
        return 2
    if not args.i_understand:
        print("Refusing --deploy-dev: pass --i-understand to acknowledge real QuickSight mutations.")
        return 2
    try:
        import boto3  # noqa: F401
    except Exception:
        print("Refusing --deploy-dev: boto3 not installed / no AWS environment.")
        return 2

    print("Guarded dev deploy is intentionally not implemented in the portfolio MVP.")
    print(f"Would deploy {len(plan['ordered_actions'])} actions using profile '{args.profile}'.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
