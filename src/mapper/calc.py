"""Translate calculated fields via the GenAI provider into a mapping doc."""

from __future__ import annotations

from typing import Any

from ..generator.base import GenAIProvider


def map_calculations(
    metadata: dict[str, Any], provider: GenAIProvider
) -> dict[str, Any]:
    translations = [
        provider.translate_calculation(calc)
        for calc in metadata.get("calculated_fields", [])
    ]
    return {
        "workbook_id": metadata["workbook_id"],
        "provider": provider.name,
        "calculations": [t.to_dict() for t in translations],
    }
