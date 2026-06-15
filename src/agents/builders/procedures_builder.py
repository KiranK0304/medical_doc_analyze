# src/agents/builders/procedures_builder.py
"""
ProceduresBuilder — extracts all procedures from clinical pages.

List-based builder. Returns List[Procedure] in result.section_data.

Usage:
    builder = ProceduresBuilder(extraction_json=..., api_key="...")
    result = builder.build()
    state.procedures = result.section_data or []
"""

from datetime import date
from typing import List, Optional

from src.schemas.clinical import Procedure

from src.agents.builders.base_builder import BaseSectionBuilder
from src.agents.prompts.procedures_prompt import (
    SYSTEM_INSTRUCTION,
    build_user_prompt,
)


class ProceduresBuilder(BaseSectionBuilder):
    """Extracts procedures and interventions from clinical pages."""

    SECTION_NAME = "procedures"
    BUILDER_NAME = "ProceduresBuilder"
    REQUIRED_FIELDS = ["procedure_name"]

    def _get_system_instruction(self) -> str:
        return SYSTEM_INSTRUCTION

    def _build_user_prompt(self) -> str:
        return build_user_prompt(self.extraction_json)

    def _parse_section_model(self, llm_response: dict) -> Optional[List[Procedure]]:
        """Parse the 'procedures' array into a list of Procedure models."""
        raw_list = llm_response.get("procedures")
        if not raw_list or not isinstance(raw_list, list):
            return None

        procedures: List[Procedure] = []
        for raw in raw_list:
            if not isinstance(raw, dict):
                continue

            self.clean_null_strings(raw)
            self._coerce_date(raw, "procedure_date")

            try:
                procedures.append(Procedure(**raw))
            except Exception:
                continue

        return procedures if procedures else None

    # ── Helpers ───────────────────────────────────────────────

    @staticmethod
    def _coerce_date(raw: dict, field_name: str) -> None:
        """Convert a date string to a date object, or None."""
        value = raw.get(field_name)
        if isinstance(value, str):
            try:
                raw[field_name] = date.fromisoformat(value)
            except (ValueError, TypeError):
                raw[field_name] = None
