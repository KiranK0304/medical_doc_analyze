# src/agents/builders/patient_details_builder.py
"""
PatientDetailsBuilder — extracts patient demographics from clinical pages.

Extends BaseSectionBuilder, so it only needs to define:
    - The section-specific prompt
    - The model parsing logic
    - Any extra flags (e.g. missing patient_id placeholder)

Usage:
    builder = PatientDetailsBuilder(
        extraction_json=loaded_json,
        api_key="...",
        source_document="clinical_chart.pdf",
    )
    result = builder.build()

    # Then update ClinicalState:
    state.patient_details = result.section_data
    state.flags.extend(result.flags)
    state.conflicts.extend(result.conflicts)
    state.completeness_tracker["patient_details"] = result.section_status
"""

from typing import List, Optional

from src.schemas.base import Flag, ReviewItem, Severity
from src.schemas.clinical import PatientDetails

from src.agents.builders.base_builder import BaseSectionBuilder
from src.agents.prompts.patient_details_prompt import (
    SYSTEM_INSTRUCTION,
    build_user_prompt,
)


class PatientDetailsBuilder(BaseSectionBuilder):
    """
    Reads extracted page transcriptions, asks the LLM to identify
    patient demographics, and returns a structured BuilderResult.
    """

    SECTION_NAME = "patient_details"
    BUILDER_NAME = "PatientDetailsBuilder"
    REQUIRED_FIELDS = ["patient_id", "patient_name", "age", "gender"]

    # ── Abstract method implementations ──────────────────────

    def _get_system_instruction(self) -> str:
        return SYSTEM_INSTRUCTION

    def _build_user_prompt(self) -> str:
        return build_user_prompt(self.extraction_json)

    def _parse_section_model(self, llm_response: dict) -> Optional[PatientDetails]:
        """
        Extract the patient_details dict from the LLM response and
        construct a PatientDetails model.

        If patient_id is missing, generates a placeholder from case_id.
        """
        raw = llm_response.get("patient_details")
        if not raw or not isinstance(raw, dict):
            return None

        # Ensure patient_id exists (it's a required field on the model)
        if not raw.get("patient_id"):
            raw["patient_id"] = f"UNKNOWN_{self.case_id}"

        self.clean_null_strings(raw)

        try:
            return PatientDetails(**raw)
        except Exception:
            return None

    # ── Section-specific flag logic ──────────────────────────

    def _parse_flags(self, llm_response: dict) -> List[Flag]:
        """
        Extends the base flag parsing with a patient_id-specific
        check: if no ID was found, surface a HIGH severity flag.
        """
        flags = super()._parse_flags(llm_response)

        raw_details = llm_response.get("patient_details", {})
        if not raw_details.get("patient_id"):
            flags.append(
                Flag(
                    flag_type="MissingField",
                    name="patient_id",
                    description=(
                        "Patient ID not found in any source page. "
                        f"Auto-generated placeholder: UNKNOWN_{self.case_id}"
                    ),
                    review_required=ReviewItem(
                        issue="Missing patient identifier",
                        reason="No patient ID or MRN found in the clinical chart",
                        severity=Severity.HIGH,
                    ),
                )
            )

        return flags
