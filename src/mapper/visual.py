"""Map worksheets/dashboards to QuickSight visuals and a layout mapping doc."""

from __future__ import annotations

from typing import Any

from ..generator.base import GenAIProvider


def map_visuals(
    metadata: dict[str, Any], provider: GenAIProvider
) -> tuple[dict[str, Any], str]:
    """Return (visuals_doc, layout_mapping_markdown)."""
    worksheets = metadata.get("worksheets", [])
    mapped = [provider.map_visual(ws) for ws in worksheets]
    by_id = {m["worksheet_id"]: m for m in mapped}

    visuals_doc = {
        "workbook_id": metadata["workbook_id"],
        "provider": provider.name,
        "visuals": mapped,
        "dashboards": [
            {
                "tableau_id": db["id"],
                "tableau_name": db["name"],
                "quicksight_dashboard_id": f"migration-{metadata['workbook_id']}-{db['id']}-dashboard",
                "quicksight_analysis_id": f"migration-{metadata['workbook_id']}-{db['id']}-analysis",
                "worksheets": db.get("worksheets", []),
                "filters": db.get("filters", []),
                "parameters": db.get("parameters", []),
            }
            for db in metadata.get("dashboards", [])
        ],
    }

    layout_md = _render_layout_markdown(metadata, mapped, by_id)
    return visuals_doc, layout_md


def _render_layout_markdown(
    metadata: dict[str, Any],
    mapped: list[dict[str, Any]],
    by_id: dict[str, dict[str, Any]],
) -> str:
    lines: list[str] = []
    lines.append(f"# Layout Mapping \u2014 {metadata.get('name', metadata['workbook_id'])}")
    lines.append("")
    lines.append(
        "Approximate Tableau \u2192 QuickSight visual mapping. Gaps are surfaced (not hidden) "
        "for human review. Pixel-perfect parity is **not** a goal of v1."
    )
    lines.append("")
    lines.append("## Worksheet visual mapping")
    lines.append("")
    lines.append("| Worksheet | Tableau chart | QuickSight visual | Confidence | Gap |")
    lines.append("|-----------|---------------|-------------------|------------|-----|")
    for m in mapped:
        gap = m["gap"] or "\u2014"
        lines.append(
            f"| {m['worksheet_name']} | {m['tableau_chart_type']} | "
            f"{m['quicksight_visual_type']} | {m['confidence']} | {gap} |"
        )
    lines.append("")

    gaps = [m for m in mapped if m["gap"]]
    lines.append("## Documented gaps")
    lines.append("")
    if gaps:
        for m in gaps:
            lines.append(f"- **{m['worksheet_name']}**: {m['gap']} (non-blocking, review color/encoding fidelity).")
    else:
        lines.append("- None.")
    lines.append("")

    lines.append("## Dashboards")
    lines.append("")
    for db in metadata.get("dashboards", []):
        lines.append(f"### {db['name']}")
        sheet_names = [by_id.get(ws, {}).get("worksheet_name", ws) for ws in db.get("worksheets", [])]
        lines.append(f"- Visuals: {', '.join(sheet_names) if sheet_names else 'none'}")
        lines.append(f"- Filters as QuickSight controls: {', '.join(db.get('filters', [])) or 'none'}")
        lines.append(f"- Parameters as QuickSight parameters: {', '.join(db.get('parameters', [])) or 'none'}")
        lines.append("")

    lines.append("## Not auto-migrated (manual follow-up)")
    lines.append("")
    lines.append("- Tableau LOD expressions (FIXED/INCLUDE/EXCLUDE) \u2192 rebuild with QuickSight level-aware calcs.")
    lines.append("- Table calculations (RUNNING_*, WINDOW_*, INDEX, RANK) \u2192 rebuild on the QuickSight visual.")
    lines.append("- ATTR() aggregation \u2192 confirm intended aggregation in QuickSight.")
    lines.append("- Custom color palettes, tooltips, and exact sizing \u2192 manual styling.")
    lines.append("")
    return "\n".join(lines)
