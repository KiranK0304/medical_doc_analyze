# src/agents/builders/base_builder.py
"""
BaseSectionBuilder — abstract base class for all ClinicalState section builders.

Encapsulates the common pipeline that every builder follows:
    1. Build prompt from extraction JSON
    2. Call the LLM
    3. Parse the response into section model + flags + conflicts
    4. Attach evidence & confidence
    5. Compute section status

Subclasses only need to implement three methods:
    - _get_system_instruction()
    - _build_user_prompt()
    - _parse_section_model(llm_response)

This eliminates duplication across PatientDetailsBuilder,
AdmissionDetailsBuilder, and every future section builder.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, List, Optional

from src.schemas.base import (
    ClinicalBase,
    Confidence,
    Evidence,
    Flag,
    ReviewItem,
    Severity,
)
from src.schemas.state import Conflict, SectionStatus

from src.agents.utils.llm_client import call_llm
from src.agents.utils.evidence_factory import create_evidence
from src.agents.utils.conflict_detector import build_conflicts_from_llm_response
from src.agents.utils.section_status_calculator import compute_section_status


# ── Module-level constants ────────────────────────────────────
# Moved out of the loop so it isn't recreated on every flag parse.
SEVERITY_MAP = {
    "low": Severity.LOW,
    "medium": Severity.MEDIUM,
    "high": Severity.HIGH,
    "critical": Severity.CRITICAL,
}

# Strings the LLM sometimes emits instead of a real null.
_NULL_STRINGS = frozenset({"null", "none", "n/a", ""})


@dataclass
class BuilderResult:
    """
    Generic container for any section builder's output.

    `section_data` holds the populated Pydantic model (e.g. PatientDetails,
    AdmissionDetails).  The caller accesses it and assigns it to the
    appropriate ClinicalState field.
    """
    section_data: Optional[Any] = None
    flags: List[Flag] = field(default_factory=list)
    conflicts: List[Conflict] = field(default_factory=list)
    section_status: SectionStatus = field(default_factory=SectionStatus)


class BaseSectionBuilder(ABC):
    """
    Abstract base for all ClinicalState section builders.

    Subclass contract:
        SECTION_NAME   — key in ClinicalState (e.g. "admission_details")
        BUILDER_NAME   — human-readable name for logs / status
        REQUIRED_FIELDS — fields that must be non-null for COMPLETE status

        _get_system_instruction() -> str
        _build_user_prompt()      -> str
        _parse_section_model(llm_response) -> Optional[ClinicalBase]
    """

    SECTION_NAME: str
    BUILDER_NAME: str
    REQUIRED_FIELDS: List[str]

    def __init__(
        self,
        extraction_json: dict,
        api_key: str,
        source_document: str = "unknown_document",
        case_id: str = "unknown_case",
    ):
        self.extraction_json = extraction_json
        self.api_key = api_key
        self.source_document = source_document
        self.case_id = case_id

    # ── Abstract methods (subclasses MUST implement) ─────────

    @abstractmethod
    def _get_system_instruction(self) -> str:
        """Return the system instruction for the LLM call."""

    @abstractmethod
    def _build_user_prompt(self) -> str:
        """Build the full user prompt from extraction JSON."""

    @abstractmethod
    def _parse_section_model(
        self, llm_response: dict
    ) -> Optional[ClinicalBase]:
        """
        Parse the LLM response dict and return the section's
        Pydantic model, or None if nothing was extracted.
        """

    # ── Main pipeline (shared by all builders) ───────────────

    def build(self) -> BuilderResult:
        """
        Execute the full builder pipeline:
          1. Build the LLM prompt
          2. Call the LLM
          3. Parse the response into section model + flags + conflicts
          4. Attach evidence & confidence to the model
          5. Compute section status

        Returns:
            BuilderResult with section_data, flags, conflicts,
            and section_status.
        """
        result = BuilderResult()

        # ── Step 1: Build the prompt ──────────────────────────
        user_prompt = self._build_user_prompt()

        # ── Step 2: Call the LLM ──────────────────────────────
        try:
            llm_response = call_llm(
                api_key=self.api_key,
                system_instruction=self._get_system_instruction(),
                user_prompt=user_prompt,
            )
        except Exception as e:
            result.flags.append(self._make_llm_error_flag(e))
            result.section_status = compute_section_status(
                model_instance=None,
                required_fields=self.REQUIRED_FIELDS,
                builder_name=self.BUILDER_NAME,
                notes=f"LLM call failed: {e}",
            )
            return result

        # ── Step 3: Parse ─────────────────────────────────────
        result.section_data = self._parse_section_model(llm_response)
        result.flags = self._parse_flags(llm_response)
        result.conflicts = self._parse_conflicts(llm_response)

        # ── Step 4: Evidence & confidence ─────────────────────
        if result.section_data is not None:
            self._attach_evidence_and_confidence(
                result.section_data, llm_response
            )

        # ── Step 5: Section status ────────────────────────────
        result.section_status = compute_section_status(
            model_instance=result.section_data,
            required_fields=self.REQUIRED_FIELDS,
            builder_name=self.BUILDER_NAME,
        )

        return result

    # ── Shared helpers ────────────────────────────────────────

    @staticmethod
    def clean_null_strings(raw: dict) -> dict:
        """
        Replace LLM artefact strings ("null", "None", "N/A", "")
        with actual None so Pydantic treats them as missing.
        """
        for key, value in raw.items():
            if isinstance(value, str) and value.lower() in _NULL_STRINGS:
                raw[key] = None
        return raw

    def _make_llm_error_flag(self, error: Exception) -> Flag:
        """Create a standardised error flag when the LLM call fails."""
        return Flag(
            flag_type="ExtractionFailure",
            name=f"{self.SECTION_NAME}_llm_error",
            description=f"LLM call failed: {error}",
            review_required=ReviewItem(
                issue=f"LLM extraction failed for {self.SECTION_NAME}",
                reason=str(error),
                severity=Severity.CRITICAL,
            ),
        )

    def _parse_flags(self, llm_response: dict) -> List[Flag]:
        """
        Convert the 'flags' array from the LLM response into Flag objects.

        Subclasses may extend this (call super() first) to add
        section-specific flags (e.g. missing ID placeholders).
        """
        flags: List[Flag] = []

        raw_flags = llm_response.get("flags", [])
        for rf in raw_flags:
            if not isinstance(rf, dict):
                continue

            severity_str = rf.get("severity", "medium").lower()
            severity = SEVERITY_MAP.get(severity_str, Severity.MEDIUM)

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
        Conflict schema objects using the shared utility.
        """
        raw_conflicts = llm_response.get("conflicts", [])
        if not raw_conflicts:
            return []

        return build_conflicts_from_llm_response(
            conflict_entries=raw_conflicts,
            section=self.SECTION_NAME,
            source_document=self.source_document,
        )

    def _attach_evidence_and_confidence(
        self,
        model: ClinicalBase,
        llm_response: dict,
    ) -> None:
        """
        Attach evidence list and confidence score from the LLM
        response to any ClinicalBase model (mutates in-place).
        """
        # Evidence
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
                    section_name=self.SECTION_NAME,
                )
            )
        model.evidence = evidence_list

        # Confidence
        raw_confidence = llm_response.get("confidence", {})
        if raw_confidence and isinstance(raw_confidence, dict):
            score = raw_confidence.get("overall_score")
            if score is not None:
                model.confidence = Confidence(
                    confidence_score=float(score),
                    confidence_reason=raw_confidence.get("reason"),
                )
