"""Build the ordered QuickSight API plan from a migration package.

The plan is emitted in dependency order (DataSource -> DataSet -> Analysis ->
Dashboard) using idempotent ``migration-{workbook}-{resource}`` names. This
module never calls AWS; it only produces a plan for dry-run review and for the
guarded ``--deploy-dev`` executor to consume.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def _load_yaml(path: Path) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def build_plan(package_root: str | Path) -> dict[str, Any]:
    package_root = Path(package_root)
    mappings = package_root / "mappings"

    datasources = _load_yaml(mappings / "datasources.yaml")
    datasets = _load_yaml(mappings / "datasets.yaml")
    visuals = _load_yaml(mappings / "visuals.yaml")

    actions: list[dict[str, Any]] = []

    for ds in datasources["datasources"]:
        if not ds["supported"]:
            actions.append(
                {
                    "action": "SKIP_DATA_SOURCE",
                    "resource_id": ds["quicksight_data_source_id"],
                    "reason": "unsupported connection; manual follow-up required",
                }
            )
            continue
        actions.append(
            {
                "action": "CreateDataSource",
                "resource_id": ds["quicksight_data_source_id"],
                "type": ds["quicksight_type"],
                "idempotency": "reuse-if-exists",
            }
        )

    for dataset in datasets["datasets"]:
        actions.append(
            {
                "action": "CreateDataSet",
                "resource_id": dataset["quicksight_dataset_id"],
                "physical_table": dataset["physical_table"],
                "import_mode": dataset["import_mode"],
                "column_count": len(dataset["columns"]),
            }
        )

    for db in visuals["dashboards"]:
        actions.append(
            {
                "action": "CreateAnalysis",
                "resource_id": db["quicksight_analysis_id"],
                "source_dashboard": db["tableau_name"],
                "visual_count": len(db["worksheets"]),
            }
        )
        actions.append(
            {
                "action": "CreateDashboard",
                "resource_id": db["quicksight_dashboard_id"],
                "from_analysis": db["quicksight_analysis_id"],
            }
        )

    return {
        "workbook_id": datasources["workbook_id"],
        "ordered_actions": actions,
        "summary": _summarize(actions),
    }


def _summarize(actions: list[dict[str, Any]]) -> dict[str, int]:
    summary: dict[str, int] = {}
    for action in actions:
        summary[action["action"]] = summary.get(action["action"], 0) + 1
    return summary
