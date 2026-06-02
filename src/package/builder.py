"""Build the migration package from metadata using a GenAI provider.

Writes the S3-style package layout (mappings/, generated/) under an output root
and returns an in-memory handle the validator and deploy planner consume.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..common import write_text, write_yaml
from ..generator.base import GenAIProvider
from ..mapper import map_calculations, map_datasources, map_visuals


@dataclass
class MigrationPackage:
    workbook_id: str
    run_id: str
    output_root: Path
    datasources: dict[str, Any]
    datasets: dict[str, Any]
    calculations: dict[str, Any]
    visuals: dict[str, Any]
    layout_markdown: str
    q_topics: dict[str, Any]
    manifest: dict[str, Any]


def build_package(
    metadata: dict[str, Any],
    provider: GenAIProvider,
    output_root: str | Path,
) -> MigrationPackage:
    output_root = Path(output_root)
    run_id = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    datasources, datasets = map_datasources(metadata)
    calculations = map_calculations(metadata, provider)
    visuals, layout_md = map_visuals(metadata, provider)
    q_topics = provider.generate_q_topics(metadata)

    mappings_dir = output_root / "mappings"
    generated_dir = output_root / "generated"

    write_yaml(mappings_dir / "datasources.yaml", datasources)
    write_yaml(mappings_dir / "datasets.yaml", datasets)
    write_yaml(mappings_dir / "calculations.yaml", calculations)
    write_yaml(mappings_dir / "visuals.yaml", visuals)
    write_text(generated_dir / "layout_mapping.md", layout_md)
    write_yaml(generated_dir / "q_topics.yaml", q_topics)

    manifest = {
        "workbook_id": metadata["workbook_id"],
        "workbook_name": metadata.get("name"),
        "run_id": run_id,
        "tableau_version": metadata.get("tableau_version"),
        "source_hash": metadata.get("source_hash"),
        "genai_provider": provider.name,
        "state": "generated",
        "approver": None,
    }
    write_yaml(output_root / "manifest.yaml", manifest)

    return MigrationPackage(
        workbook_id=metadata["workbook_id"],
        run_id=run_id,
        output_root=output_root,
        datasources=datasources,
        datasets=datasets,
        calculations=calculations,
        visuals=visuals,
        layout_markdown=layout_md,
        q_topics=q_topics,
        manifest=manifest,
    )
