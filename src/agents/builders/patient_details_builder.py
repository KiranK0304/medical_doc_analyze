# src/agents/builders/patient_details_builder.py
"""
PatientDetailsBuilder — the first section builder in the reasoning layer.

Takes the extracted markdown JSON (from VLM extraction), sends it to the
LLM with a focused prompt, and produces:
    - PatientDetails (populated Pydantic model)
    - List[Flag] (any data quality issues)
    - List[Conflict] (contradictions across pages)
    - SectionStatus (completeness assessment)

Usage:
    builder = PatientDetailsBuilder(
        extraction_json=loaded_json,
        api_key="...",
        source_document="clinical_chart.pdf",
    )
    result = builder.build()

    # Then update ClinicalState:
    state.patient_details = result.patient_details
    state.flags.extend(result.flags)
    state.conflicts.extend(result.conflicts)
    state.completeness_tracker["patient_details"] = result.section_status
"""

from dataclasses import dataclass, field
from typing import List, Optional

from src.schemas.base import Evidence, Confidence, Flag, ReviewItem, Severity
from src.schemas.clinical import PatientDetails
from src.schemas.state import Conflict, SectionStatus

from src.agents.prompts.patient_details_prompt import (
    SYSTEM_INSTRUCTION,
    build_user_prompt,
)
from src.agents.utils.llm_client import call_llm
from src.agents.utils.evidence_factory import (
    create_evidence,
    create_evidence_list_from_llm_response,
)
from src.agents.utils.conflict_detector import build_conflicts_from_llm_response
from src.agents.utils.section_status_calculator import compute_section_status


# Fields we consider required for a "complete" patient_details section.
# These drive the SectionStatus calculation.
REQUIRED_FIELDS = [
    "patient_id",
    "patient_name",
    "age",
    "gender",
]

BUILDER_NAME = "PatientDetailsBuilder"


@dataclass
class BuilderResult:
    """
    Container for everything the builder produces.
    The caller uses this to update ClinicalState in a single step.
    """
    patient_details: Optional[PatientDetails] = None
    flags: List[Flag] = field(default_factory=list)
    conflicts: List[Conflict] = field(default_factory=list)
    section_status: SectionStatus = field(default_factory=SectionStatus)


class PatientDetailsBuilder:
    """
    Reads extracted page transcriptions, asks the LLM to identify
    patient demographics, and returns a structured BuilderResult.
    """

    def __init__(
        self,
        extraction_json: dict,
        api_key: str,
        source_document: str = "unknown_document",
        case_id: str = "unknown_case",
    ):
        """
        Args:
            extraction_json: The full extraction payload (with 'metadata'
                             and 'pages' keys) produced by vlm_extractor.
            api_key: Gemini API key.
            source_document: Identifier for the source PDF file.
            case_id: Case ID used as fallback for patient_id generation.
        """
        self.extraction_json = extraction_json
        self.api_key = api_key
        self.source_document = source_document
        self.case_id = case_id

    def build(self) -> BuilderResult:
        """
        Execute the full builder pipeline:
          1. Build the LLM prompt from extraction JSON
          2. Call the LLM
          3. Parse the response into schema objects
          4. Compute section status

        Returns:
            BuilderResult with patient_details, flags, conflicts,
            and section_status.
        """
        result = BuilderResult()

        # ── Step 1: Build the prompt ─────────────────────────
        user_prompt = build_user_prompt(self.extraction_json)

        # ── Step 2: Call the LLM ─────────────────────────────
        try:
            llm_response = call_llm(
                api_key=self.api_key,
                system_instruction=SYSTEM_INSTRUCTION,
                user_prompt=user_prompt,
            )
        except Exception as e:
            # If the LLM call fails, return an empty result with a flag
            result.flags.append(
                Flag(
                    flag_type="ExtractionFailure",
                    name="patient_details_llm_error",
                    description=f"LLM call failed: {e}",
                    review_required=ReviewItem(
                        issue="LLM extraction failed for patient details",
                        reason=str(e),
                        severity=Severity.CRITICAL,
                    ),
                )
            )
            result.section_status = compute_section_status(
                model_instance=None,
                required_fields=REQUIRED_FIELDS,
                builder_name=BUILDER_NAME,
                notes=f"LLM call failed: {e}",
            )
            return result

        # ── Step 3: Parse the LLM response ───────────────────
        result.patient_details = self._parse_patient_details(llm_response)
        result.flags = self._parse_flags(llm_response)
        result.conflicts = self._parse_conflicts(llm_response)

        # Attach evidence and confidence to the PatientDetails model
        if result.patient_details is not None:
            result.patient_details = self._attach_evidence_and_confidence(
                result.patient_details, llm_response
            )

        # ── Step 4: Compute section status ───────────────────
        result.section_status = compute_section_status(
            model_instance=result.patient_details,
            required_fields=REQUIRED_FIELDS,
            builder_name=BUILDER_NAME,
        )

        return result

    # ──────────────────────────────────────────────────────────
    # Private parsing helpers
    # ──────────────────────────────────────────────────────────

    def _parse_patient_details(self, llm_response: dict) -> Optional[PatientDetails]:
        """
        Extract the patient_details dict from the LLM response and
        construct a PatientDetails model.

        If patient_id is missing, generates a placeholder from case_id
        and adds a flag (handled by the caller via the flags list).
        """
        raw = llm_response.get("patient_details")
        if not raw or not isinstance(raw, dict):
            return None

        # Ensure patient_id exists (it's a required field on the model)
        if not raw.get("patient_id"):
            raw["patient_id"] = f"UNKNOWN_{self.case_id}"

        # Clean up None-string artifacts from LLM responses
        for key, value in raw.items():
            if isinstance(value, str) and value.lower() in ("null", "none", "n/a", ""):
                raw[key] = None

        try:
            return PatientDetails(**raw)
        except Exception:
            # If Pydantic validation fails, return None and let
            # the section_status reflect EMPTY
            return None

    def _parse_flags(self, llm_response: dict) -> List[Flag]:
        """
        Convert the 'flags' array from the LLM response into Flag objects.
        Also adds a flag if patient_id was missing and auto-generated.
        """
        flags: List[Flag] = []

        # Check if patient_id was auto-generated
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

        # Parse LLM-reported flags
        raw_flags = llm_response.get("flags", [])
        for rf in raw_flags:
            if not isinstance(rf, dict):
                continue

            severity_str = rf.get("severity", "medium").lower()
            severity_map = {
                "low": Severity.LOW,
                "medium": Severity.MEDIUM,
                "high": Severity.HIGH,
                "critical": Severity.CRITICAL,
            } #do we need to create this in the loop?
            severity = severity_map.get(severity_str, Severity.MEDIUM)

            flags.append(
                Flag(
                    flag_type="DataQuality",
                    name=rf.get("field_name", "unknown_field"),
                    description=rf.get("issue", ""),
                    review_required=ReviewItem(
                        issue=rf.get("issue", "Data quality concern"),
                        reason=rf.get("issue", "Flagged by LLM during extraction"),
                        severity=severity,
                    ),
                )
            )

        return flags

    def _parse_conflicts(self, llm_response: dict) -> List[Conflict]:
        """
        Convert the 'conflicts' array from the LLM response into
        proper Conflict schema objects using the shared utility.
        """
        raw_conflicts = llm_response.get("conflicts", [])
        if not raw_conflicts:
            return []

        return build_conflicts_from_llm_response(
            conflict_entries=raw_conflicts,
            section="patient_details",
            source_document=self.source_document,
        )

    def _attach_evidence_and_confidence(
        self,
        details: PatientDetails,
        llm_response: dict,
    ) -> PatientDetails:
        """
        Attach evidence list and confidence score from the LLM response
        to the PatientDetails model (which inherits from ClinicalBase).
        """
        # Build evidence objects
        raw_evidence = llm_response.get("evidence", [])
        evidence_list = []
        for entry in raw_evidence:
            if not isinstance(entry, dict):
                continue
            evidence_list.append(
                create_evidence(
                    source_document=self.source_document,
                    page_number=entry.get("page_number"),
                    extracted_text=entry.get("extracted_text", ""),
                    section_name="patient_details",
                )
            )
        details.evidence = evidence_list

        # Attach overall confidence
        raw_confidence = llm_response.get("confidence", {})
        if raw_confidence and isinstance(raw_confidence, dict):
            score = raw_confidence.get("overall_score")
            if score is not None:
                details.confidence = Confidence(
                    confidence_score=float(score),
                    confidence_reason=raw_confidence.get("reason"),
                )

        return details
