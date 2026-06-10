# src/agents/builders/diagnoses_builder.py
"""
DiagnosesBuilder — extracts all diagnoses from clinical pages.

First list-based builder. Unlike the singleton builders (patient_details,
admission_details), this one returns a List[Diagnosis] in
result.section_data.

Usage:
    builder = DiagnosesBuilder(
        extraction_json=loaded_json,
        api_key="...",
        source_document="clinical_chart.pdf",
    )
    result = builder.build()

    state.diagnoses = result.section_data or []
    state.flags.extend(result.flags)
    state.conflicts.extend(result.conflicts)
    state.completeness_tracker["diagnoses"] = result.section_status
"""

from datetime import date
from typing import List, Optional

from src.schemas.clinical import Diagnosis, DiagnosisType, DiagnosisStatus

from src.agents.builders.base_builder import BaseSectionBuilder
from src.agents.prompts.diagnoses_prompt import (
    SYSTEM_INSTRUCTION,
    build_user_prompt,
)


# Mapping strings the LLM might return → our enum values
_TYPE_MAP = {v.value: v for v in DiagnosisType}
_STATUS_MAP = {v.value: v for v in DiagnosisStatus}


class DiagnosesBuilder(BaseSectionBuilder):
    """
    Reads extracted page transcriptions, asks the LLM to identify
    all diagnoses, and returns a list of Diagnosis models inside
    BuilderResult.section_data.
    """

    SECTION_NAME = "diagnoses"
    BUILDER_NAME = "DiagnosesBuilder"
    REQUIRED_FIELDS = ["diagnosis_name", "diagnosis_type", "diagnosis_status"]

    # ── Abstract method implementations ──────────────────────

    def _get_system_instruction(self) -> str:
        return SYSTEM_INSTRUCTION

    def _build_user_prompt(self) -> str:
        return build_user_prompt(self.extraction_json)

    def _parse_section_model(self, llm_response: dict) -> Optional[List[Diagnosis]]:
        """
        Parse the 'diagnoses' array from the LLM response into
        a list of Diagnosis models.

        Returns None if the array is missing or empty (treated as
        EMPTY by the status calculator).
        """
        raw_list = llm_response.get("diagnoses")
        if not raw_list or not isinstance(raw_list, list):
            return None

        diagnoses: List[Diagnosis] = []
        for raw in raw_list:
            if not isinstance(raw, dict):
                continue

            self.clean_null_strings(raw)
            self._coerce_enums(raw)
            self._coerce_date(raw)

            try:
                diagnoses.append(Diagnosis(**raw))
            except Exception:
                # Skip individual items that fail validation rather
                # than losing the entire list.
                continue

        return diagnoses if diagnoses else None

    # ── Helpers ───────────────────────────────────────────────

    @staticmethod
    def _coerce_enums(raw: dict) -> None:
        """
        Map LLM string values to the correct Enum members.
        Falls back to sensible defaults if the string is unrecognised.
        """
        raw_type = (raw.get("diagnosis_type") or "").lower().strip()
        raw["diagnosis_type"] = _TYPE_MAP.get(raw_type, DiagnosisType.SECONDARY)

        raw_status = (raw.get("diagnosis_status") or "").lower().strip()
        raw["diagnosis_status"] = _STATUS_MAP.get(raw_status, DiagnosisStatus.UNKNOWN)

    @staticmethod
    def _coerce_date(raw: dict) -> None:
        """Convert diagnosis_date string to a date object, or None."""
        value = raw.get("diagnosis_date")
        if isinstance(value, str):
            try:
                raw["diagnosis_date"] = date.fromisoformat(value)
            except (ValueError, TypeError):
                raw["diagnosis_date"] = None
