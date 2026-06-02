"""Local validation engine.

Implements the subset of VALIDATION.md checks that are feasible without a live
Tableau Server or QuickSight account:

* Structural   - every referenced field exists in a mapped dataset.
* Datasource   - Tableau connection class is an auto-mappable QuickSight source.
* Calculation  - syntax (balanced/non-empty), coverage, confidence gating.
* Metric parity- precomputed fixture CSVs compared within tolerance.
* Visual       - visual count per dashboard, required filters present, gaps.

Produces a migration_report.json with PASS/WARN/FAIL and ``deploy_allowed``.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from ..common import all_dataset_fields, write_text

EPS = 1e-9


@dataclass
class ValidationConfig:
    # KPI calcs that must be high confidence (block deploy otherwise).
    kpi_calcs: list[str] = field(default_factory=lambda: ["Profit Ratio"])
    parity_tolerance_pct: float = 0.01
    visual_count_tolerance: int = 0
    require_approval_for_deploy: bool = True


def validate(
    metadata: dict[str, Any],
    package: Any,
    parity_dir: str | Path,
    config: ValidationConfig | None = None,
    approver: str | None = None,
) -> dict[str, Any]:
    config = config or ValidationConfig()
    parity_dir = Path(parity_dir)

    blockers: list[str] = []
    warnings: list[str] = []

    structural = _check_structural(metadata)
    if structural["status"] == "FAIL":
        blockers.extend(structural["errors"])

    datasource_checks = _check_datasources(package)
    for dsc in datasource_checks:
        if dsc["status"] == "FAIL":
            blockers.append(f"datasource '{dsc['name']}' unsupported connection")

    calc_summary, calc_blockers, calc_warnings = _check_calculations(package, config)
    blockers.extend(calc_blockers)
    warnings.extend(calc_warnings)

    parity_checks = _check_parity(package, parity_dir, config)
    for pc in parity_checks:
        if pc["status"] == "FAIL":
            blockers.append(f"parity scenario '{pc['scenario']}' out of tolerance")

    visual_checks, visual_warnings = _check_visuals(metadata, package, config)
    warnings.extend(visual_warnings)

    if structural["status"] != "PASS":
        warnings.extend(structural.get("warnings", []))

    fail = bool(blockers)
    if fail:
        overall = "FAIL"
    elif warnings:
        overall = "WARN"
    else:
        overall = "PASS"

    approval_recorded = approver is not None
    deploy_allowed = (not blockers) and (
        approval_recorded or not config.require_approval_for_deploy
    )

    report = {
        "workbook_id": metadata["workbook_id"],
        "run_id": package.run_id,
        "genai_provider": package.manifest.get("genai_provider"),
        "overall_status": overall,
        "structural_check": structural,
        "datasource_checks": datasource_checks,
        "calc_checks": calc_summary,
        "parity_checks": parity_checks,
        "visual_checks": visual_checks,
        "approval_recorded": approval_recorded,
        "approver": approver,
        "deploy_allowed": deploy_allowed,
        "blockers": blockers,
        "warnings": warnings,
    }

    _write_parity_csv(package.output_root, parity_checks)
    return report


def _check_structural(metadata: dict[str, Any]) -> dict[str, Any]:
    available = all_dataset_fields(metadata)
    errors: list[str] = []

    for calc in metadata.get("calculated_fields", []):
        for dep in calc.get("depends_on", []):
            if dep not in available:
                errors.append(f"calc '{calc['name']}' references missing field '{dep}'")

    for ws in metadata.get("worksheets", []):
        for fld in ws.get("fields_used", []):
            if fld not in available:
                errors.append(f"worksheet '{ws['name']}' references missing field '{fld}'")

    return {
        "status": "FAIL" if errors else "PASS",
        "fields_available": len(available),
        "errors": errors,
    }


def _check_datasources(package: Any) -> list[dict[str, Any]]:
    checks = []
    for ds in package.datasources["datasources"]:
        checks.append(
            {
                "name": ds["tableau_name"],
                "quicksight_type": ds["quicksight_type"],
                "status": "PASS" if ds["supported"] else "FAIL",
                "notes": ds["notes"],
            }
        )
    return checks


def _balanced(expr: str) -> bool:
    depth = 0
    for ch in expr:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth < 0:
                return False
    return depth == 0 and expr.count("'") % 2 == 0


def _check_calculations(
    package: Any, config: ValidationConfig
) -> tuple[dict[str, Any], list[str], list[str]]:
    calcs = package.calculations["calculations"]
    blockers: list[str] = []
    warnings: list[str] = []

    total = len(calcs)
    high = medium = low = manual = failed_syntax = 0

    for calc in calcs:
        conf = calc["confidence"]
        is_manual = calc["manual_required"]
        expr = calc["quicksight_expression"]

        if is_manual:
            manual += 1
        elif conf == "high":
            high += 1
        elif conf == "medium":
            medium += 1
        else:
            low += 1

        if not is_manual:
            if not expr or not _balanced(expr):
                failed_syntax += 1
                blockers.append(f"calc '{calc['tableau_name']}' failed syntax check")

        # Confidence gating for KPI calcs.
        if calc["tableau_name"] in config.kpi_calcs and (is_manual or conf == "low"):
            blockers.append(
                f"KPI calc '{calc['tableau_name']}' is {('manual' if is_manual else conf)} confidence"
            )

        if is_manual:
            warnings.append(f"calc '{calc['tableau_name']}' requires manual rewrite ({calc['category']})")
        elif conf in {"medium", "low"}:
            warnings.append(f"calc '{calc['tableau_name']}' is {conf} confidence; review translation")

    summary = {
        "total": total,
        "high_confidence": high,
        "medium_confidence": medium,
        "low_confidence": low,
        "manual_required": manual,
        "failed_syntax": failed_syntax,
        "coverage": "complete" if (high + medium + low + manual) == total else "incomplete",
    }
    return summary, blockers, warnings


def _check_parity(
    package: Any, parity_dir: Path, config: ValidationConfig
) -> list[dict[str, Any]]:
    spec_path = parity_dir / "parity_spec.yaml"
    if not spec_path.exists():
        return []

    with open(spec_path, "r", encoding="utf-8") as handle:
        spec = yaml.safe_load(handle)
    tolerance = float(spec.get("tolerance_pct", config.parity_tolerance_pct))

    tableau = _load_metric_csv(parity_dir / "tableau_metrics.csv")
    quicksight = _load_metric_csv(parity_dir / "quicksight_metrics.csv")

    calc_by_id = {c["tableau_calc_id"]: c for c in package.calculations["calculations"]}

    results: list[dict[str, Any]] = []
    for scenario in spec.get("scenarios", []):
        sid = scenario["id"]
        calc = calc_by_id.get(scenario.get("calc_id"))

        if calc and (calc["manual_required"] or calc["confidence"] != "high"):
            results.append(
                {
                    "scenario": sid,
                    "metric": scenario["metric"],
                    "status": "SKIP",
                    "reason": "calc not high-confidence/non-LOD; parity skipped",
                    "delta_pct": None,
                }
            )
            continue

        a = tableau.get((sid, scenario["metric"]))
        b = quicksight.get((sid, scenario["metric"]))
        if a is None or b is None:
            results.append(
                {"scenario": sid, "metric": scenario["metric"], "status": "SKIP", "reason": "missing fixture", "delta_pct": None}
            )
            continue

        delta_pct = abs(a - b) / max(abs(a), EPS)
        results.append(
            {
                "scenario": sid,
                "metric": scenario["metric"],
                "status": "PASS" if delta_pct < tolerance else "FAIL",
                "tableau_value": a,
                "quicksight_value": b,
                "delta_pct": round(delta_pct, 6),
                "tolerance_pct": tolerance,
            }
        )
    return results


def _load_metric_csv(path: Path) -> dict[tuple[str, str], float]:
    out: dict[tuple[str, str], float] = {}
    if not path.exists():
        return out
    with open(path, "r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            out[(row["scenario"], row["metric"])] = float(row["value"])
    return out


def _check_visuals(
    metadata: dict[str, Any], package: Any, config: ValidationConfig
) -> tuple[dict[str, Any], list[str]]:
    warnings: list[str] = []
    visuals = package.visuals["visuals"]
    gaps = [v["gap"] for v in visuals if v["gap"]]
    for gap in gaps:
        warnings.append(f"visual gap: {gap}")

    available = all_dataset_fields(metadata)
    dashboard_results = []
    for db in metadata.get("dashboards", []):
        expected = len(db.get("worksheets", []))
        mapped = sum(1 for v in visuals if v["worksheet_id"] in db.get("worksheets", []))
        count_ok = abs(expected - mapped) <= config.visual_count_tolerance
        missing_filters = [f for f in db.get("filters", []) if f not in available]
        if not count_ok:
            warnings.append(f"dashboard '{db['name']}' visual count mismatch")
        if missing_filters:
            warnings.append(f"dashboard '{db['name']}' filters not mapped: {missing_filters}")
        dashboard_results.append(
            {
                "dashboard": db["name"],
                "expected_visuals": expected,
                "mapped_visuals": mapped,
                "count_ok": count_ok,
                "filters_present": not missing_filters,
            }
        )

    return (
        {
            "status": "MANUAL_REVIEW",
            "dashboards": dashboard_results,
            "gaps": gaps,
        },
        warnings,
    )


def _write_parity_csv(output_root: Path, parity_checks: list[dict[str, Any]]) -> None:
    lines = ["scenario,metric,status,tableau_value,quicksight_value,delta_pct"]
    for pc in parity_checks:
        lines.append(
            ",".join(
                str(pc.get(k, ""))
                for k in ("scenario", "metric", "status", "tableau_value", "quicksight_value", "delta_pct")
            )
        )
    write_text(Path(output_root) / "validation" / "calc_parity_results.csv", "\n".join(lines) + "\n")
