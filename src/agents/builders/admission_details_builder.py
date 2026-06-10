# src/agents/builders/admission_details_builder.py
"""
AdmissionDetailsBuilder — extracts hospital admission/discharge info.

Extends BaseSectionBuilder, so it only defines:
    - The section-specific prompt
    - The model parsing logic (with date coercion)
    - An extra flag when admission_id is auto-generated

Usage:
    builder = AdmissionDetailsBuilder(
        extraction_json=loaded_json,
        api_key="...",
        source_document="clinical_chart.pdf",
    )
    result = builder.build()

    state.admission_details = result.section_data
    state.flags.extend(result.flags)
    state.conflicts.extend(result.conflicts)
    state.completeness_tracker["admission_details"] = result.section_status
"""

from datetime import date
from typing import List, Optional

from src.schemas.base import Flag, ReviewItem, Severity
from src.schemas.clinical import AdmissionDetails

from src.agents.builders.base_builder import BaseSectionBuilder
from src.agents.prompts.admission_details_prompt import (
    SYSTEM_INSTRUCTION,
    build_user_prompt,
)


class AdmissionDetailsBuilder(BaseSectionBuilder):
    """
    Reads extracted page transcriptions, asks the LLM to identify
    admission/discharge information, and returns a structured BuilderResult.
    """

    SECTION_NAME = "admission_details"
    BUILDER_NAME = "AdmissionDetailsBuilder"
    REQUIRED_FIELDS = [
        "admission_id",
        "admission_date",
        "admission_reason",
        "department",
    ]

    # ── Abstract method implementations ──────────────────────

    def _get_system_instruction(self) -> str:
        return SYSTEM_INSTRUCTION

    def _build_user_prompt(self) -> str:
        return build_user_prompt(self.extraction_json)

    def _parse_section_model(
        self, llm_response: dict
    ) -> Optional[AdmissionDetails]:
        """
        Extract admission_details from the LLM response, coerce date
        strings into date objects, and construct the Pydantic model.
        """
        raw = llm_response.get("admission_details")
        if not raw or not isinstance(raw, dict):
            return None

        # Ensure admission_id exists (required field on the model)
        if not raw.get("admission_id"):
            raw["admission_id"] = f"ADM_UNKNOWN_{self.case_id}"

        self.clean_null_strings(raw)
        self._coerce_dates(raw)

        # Ensure chief_complaints is always a list
        cc = raw.get("chief_complaints")
        if cc is None:
            raw["chief_complaints"] = []
        elif isinstance(cc, str):
            raw["chief_complaints"] = [cc]

        try:
            return AdmissionDetails(**raw)
        except Exception:
            return None

    # ── Section-specific flag logic ──────────────────────────

    def _parse_flags(self, llm_response: dict) -> List[Flag]:
        """
        Extends base flags with an admission_id-specific check:
        if no ID was found, surface a flag about the auto-generated one.
        """
        flags = super()._parse_flags(llm_response)

        raw_details = llm_response.get("admission_details", {})
        if not raw_details.get("admission_id"):
            flags.append(
                Flag(
                    flag_type="MissingField",
                    name="admission_id",
                    description=(
                        "Admission ID not found in any source page. "
                        f"Auto-generated placeholder: ADM_UNKNOWN_{self.case_id}"
                    ),
                    review_required=ReviewItem(
                        issue="Missing admission identifier",
                        reason="No admission or encounter ID found in the chart",
                        severity=Severity.HIGH,
                    ),
                )
            )

        return flags

    # ── Helpers ───────────────────────────────────────────────

    @staticmethod
    def _coerce_dates(raw: dict) -> None:
        """
        Convert date strings (YYYY-MM-DD) into date objects in-place.
        If parsing fails, sets the field to None so Pydantic
        doesn't reject it.
        """
        for field_name in ("admission_date", "discharge_date"):
            value = raw.get(field_name)
            if isinstance(value, str):
                try:
                    raw[field_name] = date.fromisoformat(value)
                except (ValueError, TypeError):
                    raw[field_name] = None
