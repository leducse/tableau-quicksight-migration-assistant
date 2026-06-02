#!/usr/bin/env python3
"""End-to-end local migration loop.

Loads sample metadata, runs the full assistant (map -> generate -> package ->
validate) with the local mock GenAI provider, and writes all artifacts plus
``validation/migration_report.json``. Runs with NO AWS credentials.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.common import load_metadata, write_json  # noqa: E402
from src.generator import get_provider  # noqa: E402
from src.package import build_package  # noqa: E402
from src.validator import ValidationConfig, validate  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the local Tableau->QuickSight migration loop")
    parser.add_argument(
        "--metadata",
        default=str(REPO_ROOT / "samples" / "demo_metadata.json"),
        help="Path to workbook metadata.json",
    )
    parser.add_argument(
        "--parity-dir",
        default=str(REPO_ROOT / "samples" / "parity_fixtures"),
        help="Directory with parity_spec.yaml + fixture CSVs",
    )
    parser.add_argument(
        "--output",
        default=str(REPO_ROOT),
        help="Package output root (mappings/, generated/, validation/)",
    )
    parser.add_argument("--use-bedrock", action="store_true", help="Opt into the guarded Bedrock provider")
    parser.add_argument(
        "--approver",
        default="demo-reviewer",
        help="Recorded approver (simulated human sign-off). Use '' to leave unapproved.",
    )
    args = parser.parse_args(argv)

    metadata = load_metadata(args.metadata)
    provider = get_provider(use_bedrock=args.use_bedrock)
    print(f"GenAI provider: {provider.name}")

    package = build_package(metadata, provider, args.output)
    print(f"Built package for '{package.workbook_id}' (run {package.run_id}) at {package.output_root}")

    approver = args.approver or None
    report = validate(
        metadata,
        package,
        args.parity_dir,
        config=ValidationConfig(),
        approver=approver,
    )

    report_path = Path(args.output) / "validation" / "migration_report.json"
    write_json(report_path, report)

    print("\n=== Migration report ===")
    print(f"overall_status : {report['overall_status']}")
    print(f"deploy_allowed : {report['deploy_allowed']}")
    print(f"calc_checks    : {report['calc_checks']}")
    print(f"parity         : {[(p['scenario'], p['status']) for p in report['parity_checks']]}")
    print(f"blockers       : {report['blockers']}")
    print(f"warnings       : {len(report['warnings'])}")
    print(f"\nReport written to: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
