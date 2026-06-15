# src/agents/builders/discharge_status_builder.py
"""
DischargeStatusBuilder — extracts discharge condition and status.

Singleton builder. Returns Optional[DischargeStatus] in result.section_data.

Usage:
    builder = DischargeStatusBuilder(extraction_json=..., api_key="...")
    result = builder.build()
    state.discharge_status = result.section_data
"""

from typing import Optional

from src.schemas.clinical import DischargeStatus

from src.agents.builders.base_builder import BaseSectionBuilder
from src.agents.prompts.discharge_status_prompt import (
    SYSTEM_INSTRUCTION,
    build_user_prompt,
)


class DischargeStatusBuilder(BaseSectionBuilder):
    """Extracts the patient's condition at discharge."""

    SECTION_NAME = "discharge_status"
    BUILDER_NAME = "DischargeStatusBuilder"
    REQUIRED_FIELDS = ["discharge_condition"]

    def _get_system_instruction(self) -> str:
        return SYSTEM_INSTRUCTION

    def _build_user_prompt(self) -> str:
        return build_user_prompt(self.extraction_json)

    def _parse_section_model(self, llm_response: dict) -> Optional[DischargeStatus]:
        """
        Parse 'discharge_status' from the LLM response.
        All fields are plain strings, so only null-string cleaning is needed.
        """
        raw = llm_response.get("discharge_status")
        if not raw or not isinstance(raw, dict):
            return None

        self.clean_null_strings(raw)

        try:
            return DischargeStatus(**raw)
        except Exception:
            return None
