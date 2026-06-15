# src/agents/builders/medications_builder.py
"""
MedicationsBuilder — extracts all medications from clinical pages.

List-based builder. Returns List[Medication] in result.section_data.

Usage:
    builder = MedicationsBuilder(extraction_json=..., api_key="...")
    result = builder.build()
    state.medications = result.section_data or []
"""

from datetime import date
from typing import List, Optional

from src.schemas.clinical import Medication, MedicationStatus

from src.agents.builders.base_builder import BaseSectionBuilder
from src.agents.prompts.medications_prompt import (
    SYSTEM_INSTRUCTION,
    build_user_prompt,
)


# Mapping strings the LLM might return → our enum values
_STATUS_MAP = {v.value: v for v in MedicationStatus}


class MedicationsBuilder(BaseSectionBuilder):
    """Extracts medications from clinical pages."""

    SECTION_NAME = "medications"
    BUILDER_NAME = "MedicationsBuilder"
    REQUIRED_FIELDS = ["medication_name", "status"]

    def _get_system_instruction(self) -> str:
        return SYSTEM_INSTRUCTION

    def _build_user_prompt(self) -> str:
        return build_user_prompt(self.extraction_json)

    def _parse_section_model(self, llm_response: dict) -> Optional[List[Medication]]:
        """Parse the 'medications' array into a list of Medication models."""
        raw_list = llm_response.get("medications")
        if not raw_list or not isinstance(raw_list, list):
            return None

        medications: List[Medication] = []
        for raw in raw_list:
            if not isinstance(raw, dict):
                continue

            self.clean_null_strings(raw)
            self._coerce_status(raw)
            self._coerce_dates(raw)

            try:
                medications.append(Medication(**raw))
            except Exception:
                continue

        return medications if medications else None

    # ── Helpers ───────────────────────────────────────────────

    @staticmethod
    def _coerce_status(raw: dict) -> None:
        """Map LLM status string to MedicationStatus enum."""
        raw_status = (raw.get("status") or "").lower().strip()
        raw["status"] = _STATUS_MAP.get(raw_status, MedicationStatus.UNKNOWN)

    @staticmethod
    def _coerce_dates(raw: dict) -> None:
        """Convert start_date and end_date strings to date objects."""
        for field_name in ("start_date", "end_date"):
            value = raw.get(field_name)
            if isinstance(value, str):
                try:
                    raw[field_name] = date.fromisoformat(value)
                except (ValueError, TypeError):
                    raw[field_name] = None
