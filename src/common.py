"""Shared IO helpers and small utilities used across the assistant."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml


def load_metadata(path: str | Path) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def write_yaml(path: str | Path, data: Any) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        yaml.safe_dump(data, handle, sort_keys=False, default_flow_style=False)


def write_json(path: str | Path, data: Any) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2)
        handle.write("\n")


def write_text(path: str | Path, text: str) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)


def slugify(value: str) -> str:
    out = []
    for ch in value.lower():
        if ch.isalnum():
            out.append(ch)
        elif ch in {" ", "_", "-", "."}:
            out.append("-")
    slug = "".join(out)
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug.strip("-")


def all_dataset_fields(metadata: dict[str, Any]) -> set[str]:
    """Every physical field plus calculated field name available in a workbook."""
    fields: set[str] = set()
    for ds in metadata.get("datasources", []):
        for table in ds.get("tables", []):
            for field in table.get("fields", []):
                fields.add(field["name"])
    for calc in metadata.get("calculated_fields", []):
        fields.add(calc["name"])
    return fields
