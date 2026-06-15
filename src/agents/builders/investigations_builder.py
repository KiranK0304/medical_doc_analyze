# src/agents/builders/investigations_builder.py
"""
InvestigationsBuilder — extracts all investigations from clinical pages.

List-based builder. Returns List[Investigation] in result.section_data.

Usage:
    builder = InvestigationsBuilder(extraction_json=..., api_key="...")
    result = builder.build()
    state.investigations = result.section_data or []
"""

from datetime import date
from typing import List, Optional

from src.schemas.clinical import Investigation, InvestigationCategory

from src.agents.builders.base_builder import BaseSectionBuilder
from src.agents.prompts.investigations_prompt import (
    SYSTEM_INSTRUCTION,
    build_user_prompt,
)


# Mapping strings the LLM might return → our enum values
_CATEGORY_MAP = {v.value: v for v in InvestigationCategory}


class InvestigationsBuilder(BaseSectionBuilder):
    """Extracts investigations and diagnostic tests from clinical pages."""

    SECTION_NAME = "investigations"
    BUILDER_NAME = "InvestigationsBuilder"
    REQUIRED_FIELDS = ["investigation_name", "category"]

    def _get_system_instruction(self) -> str:
        return SYSTEM_INSTRUCTION

    def _build_user_prompt(self) -> str:
        return build_user_prompt(self.extraction_json)

    def _parse_section_model(self, llm_response: dict) -> Optional[List[Investigation]]:
        """Parse the 'investigations' array into a list of Investigation models."""
        raw_list = llm_response.get("investigations")
        if not raw_list or not isinstance(raw_list, list):
            return None

        investigations: List[Investigation] = []
        for raw in raw_list:
            if not isinstance(raw, dict):
                continue

            self.clean_null_strings(raw)
            self._coerce_category(raw)
            self._coerce_date(raw)

            try:
                investigations.append(Investigation(**raw))
            except Exception:
                continue

        return investigations if investigations else None

    # ── Helpers ───────────────────────────────────────────────

    @staticmethod
    def _coerce_category(raw: dict) -> None:
        """Map LLM category string to InvestigationCategory enum."""
        raw_cat = (raw.get("category") or "").lower().strip()
        raw["category"] = _CATEGORY_MAP.get(raw_cat, InvestigationCategory.OTHER)

    @staticmethod
    def _coerce_date(raw: dict) -> None:
        """Convert investigation_date string to a date object, or None."""
        value = raw.get("investigation_date")
        if isinstance(value, str):
            try:
                raw["investigation_date"] = date.fromisoformat(value)
            except (ValueError, TypeError):
                raw["investigation_date"] = None
