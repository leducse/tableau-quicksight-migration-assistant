"""Abstract GenAI interface.

All calculation translation, visual mapping, and Amazon Q topic generation goes
through :class:`GenAIProvider`. The default implementation is fully local and
rule-based (see :mod:`src.generator.mock`); a Bedrock-backed implementation is
provided but guarded so the loop runs with no AWS credentials.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class CalcTranslation:
    """Result of translating a single Tableau calculated field."""

    tableau_calc_id: str
    tableau_name: str
    tableau_formula: str
    quicksight_name: str
    quicksight_expression: str | None
    confidence: str  # high | medium | low
    category: str  # arithmetic | conditional | date | string | lod | table_calc | other
    manual_required: bool
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "tableau_calc_id": self.tableau_calc_id,
            "tableau_name": self.tableau_name,
            "tableau_formula": self.tableau_formula,
            "quicksight_name": self.quicksight_name,
            "quicksight_expression": self.quicksight_expression,
            "confidence": self.confidence,
            "category": self.category,
            "manual_required": self.manual_required,
            "notes": self.notes,
        }


class GenAIProvider(ABC):
    """Interface for calc/visual/Q generation."""

    name: str = "abstract"

    @abstractmethod
    def translate_calculation(self, calc: dict[str, Any]) -> CalcTranslation:
        """Translate one Tableau calculated field into a QuickSight expression."""

    @abstractmethod
    def map_visual(self, worksheet: dict[str, Any]) -> dict[str, Any]:
        """Map a Tableau worksheet/chart to the nearest QuickSight visual type."""

    @abstractmethod
    def generate_q_topics(self, metadata: dict[str, Any]) -> dict[str, Any]:
        """Generate Amazon Q topic definitions from workbook metadata."""
