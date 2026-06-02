"""Local, rule-based GenAI provider.

Translates a handful of common Tableau functions into QuickSight expressions
with a confidence score, and deterministically maps visuals and Q topics. This
runs with no AWS credentials and is the default provider for the portfolio MVP.
"""

from __future__ import annotations

import re
from typing import Any

from .base import CalcTranslation, GenAIProvider

# Constructs QuickSight cannot express as a row/aggregate calculated field
# without a manual rewrite. Order matters only for note clarity.
_MANUAL_PATTERNS: list[tuple[str, str, str]] = [
    (r"\{\s*(FIXED|INCLUDE|EXCLUDE)\b", "lod", "Tableau LOD expression; rebuild with QuickSight LAC-A/LAC-W functions."),
    (r"\b(RUNNING_SUM|RUNNING_AVG|RUNNING_MIN|RUNNING_MAX|WINDOW_SUM|WINDOW_AVG)\b", "table_calc", "Tableau table calculation; rebuild as a QuickSight table calc on the visual."),
    (r"\b(INDEX|RANK|FIRST|LAST|LOOKUP|PREVIOUS_VALUE|TOTAL)\s*\(", "table_calc", "Tableau table calculation; rebuild as a QuickSight table calc on the visual."),
    (r"\bATTR\s*\(", "other", "ATTR has no direct QuickSight equivalent; verify aggregation intent."),
]

# Direct 1:1 Tableau -> QuickSight function renames (word-boundary, case-insensitive).
_FUNCTION_MAP: list[tuple[str, str]] = [
    (r"\bSUM\b", "sum"),
    (r"\bAVG\b", "avg"),
    (r"\bMIN\b", "min"),
    (r"\bMAX\b", "max"),
    (r"\bCOUNTD\b", "distinct_count"),
    (r"\bCOUNT\b", "count"),
    (r"\bUPPER\b", "toUpper"),
    (r"\bLOWER\b", "toLower"),
    (r"\bLEN\b", "strlen"),
    (r"\bABS\b", "abs"),
    (r"\bZN\b", "coalesce"),
    (r"\bISNULL\b", "isNull"),
]

_CHART_TYPE_MAP: dict[str, dict[str, Any]] = {
    "bar": {"quicksight_visual": "BarChartVisual", "confidence": "high", "gap": None},
    "line": {"quicksight_visual": "LineChartVisual", "confidence": "high", "gap": None},
    "scatter": {"quicksight_visual": "ScatterPlotVisual", "confidence": "high", "gap": None},
    "pie": {"quicksight_visual": "PieChartVisual", "confidence": "high", "gap": None},
    "heatmap": {"quicksight_visual": "HeatMapVisual", "confidence": "medium", "gap": None},
    "map": {"quicksight_visual": "GeospatialMapVisual", "confidence": "medium", "gap": None},
    "dual_axis": {
        "quicksight_visual": "ComboChartVisual",
        "confidence": "medium",
        "gap": "dual_axis \u2192 combo approx",
    },
}


def _strip_field_brackets(expr: str) -> str:
    """`[Order Date]` -> `{Order Date}` (QuickSight field reference syntax)."""
    return re.sub(r"\[([^\]]+)\]", r"{\1}", expr)


def _convert_string_literals(expr: str) -> str:
    """Tableau uses double quotes for strings; QuickSight uses single quotes."""
    return re.sub(r'"([^"]*)"', r"'\1'", expr)


def _convert_if_then(expr: str) -> tuple[str, bool]:
    """Convert a single `IF c THEN a ELSE b END` to `ifelse(c, a, b)`.

    Returns the rewritten expression and whether a conditional was handled.
    """
    pattern = re.compile(
        r"\bIF\b(.+?)\bTHEN\b(.+?)\bELSE\b(.+?)\bEND\b",
        flags=re.IGNORECASE | re.DOTALL,
    )

    def repl(match: re.Match[str]) -> str:
        cond, then, els = (g.strip() for g in match.groups())
        return f"ifelse({cond}, {then}, {els})"

    new_expr, n = pattern.subn(repl, expr)
    return new_expr, n > 0


def _convert_iif(expr: str) -> tuple[str, bool]:
    new_expr, n = re.subn(r"\bIIF\s*\(", "ifelse(", expr, flags=re.IGNORECASE)
    return new_expr, n > 0


def _convert_dates(expr: str) -> tuple[str, bool, list[str]]:
    notes: list[str] = []
    used = False

    def datediff_repl(match: re.Match[str]) -> str:
        unit, a, b = match.group(1), match.group(2).strip(), match.group(3).strip()
        period = {
            "day": "DD",
            "week": "WK",
            "month": "MM",
            "quarter": "Q",
            "year": "YYYY",
        }.get(unit.strip("'\" ").lower(), "DD")
        return f"dateDiff({a}, {b}, '{period}')"

    new_expr, n = re.subn(
        r"\bDATEDIFF\s*\(\s*('[^']*'|\"[^\"]*\")\s*,\s*([^,]+?)\s*,\s*([^)]+?)\s*\)",
        datediff_repl,
        expr,
        flags=re.IGNORECASE,
    )
    if n:
        used = True

    def year_repl(match: re.Match[str]) -> str:
        return f"extract('YYYY', {match.group(1).strip()})"

    new_expr, n2 = re.subn(
        r"\bYEAR\s*\(\s*([^)]+?)\s*\)", year_repl, new_expr, flags=re.IGNORECASE
    )
    if n2:
        used = True
        notes.append("YEAR mapped to extract('YYYY', ...); confirm date part semantics.")
    return new_expr, used, notes


class MockProvider(GenAIProvider):
    name = "mock-rule-based"

    def translate_calculation(self, calc: dict[str, Any]) -> CalcTranslation:
        formula = calc.get("formula", "").strip()
        qs_name = calc["name"]

        for pattern, category, note in _MANUAL_PATTERNS:
            if re.search(pattern, formula, flags=re.IGNORECASE):
                return CalcTranslation(
                    tableau_calc_id=calc["id"],
                    tableau_name=calc["name"],
                    tableau_formula=formula,
                    quicksight_name=qs_name,
                    quicksight_expression=None,
                    confidence="low",
                    category=category,
                    manual_required=True,
                    notes=[note],
                )

        notes: list[str] = []
        category = "arithmetic"
        expr = formula

        expr, had_if = _convert_if_then(expr)
        expr, had_iif = _convert_iif(expr)
        if had_if or had_iif:
            category = "conditional"

        expr, had_date, date_notes = _convert_dates(expr)
        if had_date:
            category = "date"
            notes.extend(date_notes)

        expr = _convert_string_literals(expr)

        renamed_string_fn = False
        for pattern, replacement in _FUNCTION_MAP:
            new_expr, n = re.subn(pattern, replacement, expr)
            if n:
                expr = new_expr
                if replacement in {"toUpper", "toLower", "strlen"} and category == "arithmetic":
                    renamed_string_fn = True
        if renamed_string_fn:
            category = "string"

        expr = _strip_field_brackets(expr)
        expr = re.sub(r"\s+", " ", expr).strip()

        confidence = "high" if category in {"arithmetic", "string"} else "medium"
        if category == "conditional":
            notes.append("Conditional rewritten to ifelse(); verify branch types.")

        return CalcTranslation(
            tableau_calc_id=calc["id"],
            tableau_name=calc["name"],
            tableau_formula=formula,
            quicksight_name=qs_name,
            quicksight_expression=expr,
            confidence=confidence,
            category=category,
            manual_required=False,
            notes=notes,
        )

    def map_visual(self, worksheet: dict[str, Any]) -> dict[str, Any]:
        chart = worksheet.get("chart_type", "bar")
        mapped = _CHART_TYPE_MAP.get(
            chart,
            {"quicksight_visual": "TableVisual", "confidence": "low", "gap": f"{chart} \u2192 table fallback"},
        )
        return {
            "worksheet_id": worksheet["id"],
            "worksheet_name": worksheet["name"],
            "tableau_chart_type": chart,
            "quicksight_visual_type": mapped["quicksight_visual"],
            "confidence": mapped["confidence"],
            "fields_used": worksheet.get("fields_used", []),
            "filters": worksheet.get("filters", []),
            "gap": mapped["gap"],
        }

    def generate_q_topics(self, metadata: dict[str, Any]) -> dict[str, Any]:
        columns: list[dict[str, Any]] = []
        seen: set[str] = set()
        for ds in metadata.get("datasources", []):
            for table in ds.get("tables", []):
                for fld in table.get("fields", []):
                    if fld["name"] in seen:
                        continue
                    seen.add(fld["name"])
                    columns.append(
                        {
                            "name": fld["name"],
                            "role": fld.get("role", "dimension"),
                            "synonyms": _synonyms(fld["name"]),
                            "description": f"{fld['name']} ({fld.get('datatype', 'string')}) from {table['name']}.",
                        }
                    )
        for calc in metadata.get("calculated_fields", []):
            if calc["name"] in seen:
                continue
            seen.add(calc["name"])
            columns.append(
                {
                    "name": calc["name"],
                    "role": calc.get("role", "measure"),
                    "synonyms": _synonyms(calc["name"]),
                    "description": f"Calculated field: {calc['name']}.",
                }
            )
        return {
            "topic": {
                "name": metadata.get("name", metadata.get("workbook_id", "Workbook")),
                "description": "Auto-generated Amazon Q topic from migrated workbook metadata.",
                "dataset": f"migration-{metadata['workbook_id']}-dataset",
                "columns": columns,
            }
        }


def _synonyms(name: str) -> list[str]:
    base = name.lower()
    syns = {base}
    if " " in base:
        syns.add(base.replace(" ", "_"))
        syns.add(base.replace(" ", ""))
    return sorted(syns)
