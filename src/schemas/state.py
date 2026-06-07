# src/schemas/state.py
"""
ClinicalState — the patient-centric intermediate knowledge representation
that flows through the agent graph between document extraction and final
PatientRecord synthesis.

ClinicalState contains ONLY clinical knowledge about the patient.
It does NOT contain raw document pages, extracted markdown, workflow
execution details, or agent runtime metadata.

The 10 clinical sections mirror PatientRecord exactly (same field names,
same Pydantic models) to keep the final synthesis a trivial shallow
transformation requiring zero LLM calls.

Two additional reasoning-only sections (conflicts, completeness_tracker)
support planner decisions and are consumed before synthesis — they do not
appear in the final PatientRecord.
"""

from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
from enum import Enum

from .base import Evidence, Confidence, Flag
from .clinical import (
    PatientDetails,
    AdmissionDetails,
    Diagnosis,
    Procedure,
    Investigation,
    Medication,
    HospitalCourse,
    DischargeStatus,
    FollowUp,
)


# ============================================================
# Reasoning-Only Models: Conflicts
# ============================================================

class ResolutionStatus(str, Enum):
    """Lifecycle of a detected conflict."""
    UNRESOLVED = "unresolved"
    RESOLVED = "resolved"
    DEFERRED = "deferred"


class CompetingValue(BaseModel):
    """
    One side of a contradiction.  For example, page 3 says
    "Amoxicillin 500 mg" while page 7 says "Amoxicillin 250 mg".
    Each variant is captured as a CompetingValue with its own
    evidence trail and confidence.
    """
    value: Any
    evidence: Evidence
    confidence: Optional[Confidence] = None


class Conflict(BaseModel):
    """
    Represents a detected contradiction between two or more pieces
    of clinical data extracted from the source documents.

    Conflicts live in ClinicalState.conflicts during reasoning.
    Once the Consensus Agent resolves a conflict, the winning value
    is written into the appropriate clinical section.  Unresolved
    conflicts are converted to Flag entries during final synthesis.
    """
    conflict_id: str
    section: str = Field(
        ...,
        description="Top-level ClinicalState section name, "
                    "e.g. 'medications', 'diagnoses'"
    )
    field_path: str = Field(
        ...,
        description="Dot-notation path to the conflicting field, "
                    "e.g. 'medications[2].dose'"
    )
    competing_values: List[CompetingValue] = Field(
        ..., min_length=2,
        description="At least two contradictory values"
    )
    resolution_status: ResolutionStatus = ResolutionStatus.UNRESOLVED
    resolved_value: Optional[Any] = None
    resolved_by: Optional[str] = Field(
        default=None,
        description="Name of the agent that resolved this conflict"
    )
    resolution_reasoning: Optional[str] = None
    detected_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    resolved_at: Optional[datetime] = None


# ============================================================
# Reasoning-Only Models: Completeness Tracker
# ============================================================

class SectionStatusValue(str, Enum):
    """Progressive readiness levels for a clinical section."""
    EMPTY = "empty"
    PARTIAL = "partial"
    COMPLETE = "complete"
    VERIFIED = "verified"


class SectionStatus(BaseModel):
    """
    Per-section readiness assessment used by the Planner Agent
    to decide what information is present, missing, or requires
    further extraction / validation passes.

    This is clinical completeness metadata (e.g. "we have no
    discharge date yet"), NOT workflow orchestration metadata.
    """
    status: SectionStatusValue = SectionStatusValue.EMPTY
    missing_fields: List[str] = Field(
        default_factory=list,
        description="Field names that are expected but not yet populated, "
                    "e.g. ['discharge_date', 'attending_physician']"
    )
    last_updated_by: Optional[str] = Field(
        default=None,
        description="Name of the agent that last assessed this section"
    )
    last_updated_at: Optional[datetime] = None
    notes: Optional[str] = None


# ============================================================
# ClinicalState — the shared agent graph state
# ============================================================

class ClinicalState(BaseModel):
    """
    Patient-centric intermediate knowledge representation.

    All agents read from and write to this state.  The 10 clinical
    sections use the exact same Pydantic models as PatientRecord so
    that the final synthesis is a shallow copy with zero LLM calls.

    Two reasoning-only sections (conflicts, completeness_tracker)
    support planner decisions during the agent graph traversal and
    are consumed before the final PatientRecord is produced.
    """

    # ── Identifiers ──────────────────────────────────────────
    case_id: str = Field(
        ...,
        description="Unique identifier for this patient case"
    )
    schema_version: str = Field(
        default="1.0.0",
        description="ClinicalState schema version for forward compatibility"
    )

    # ── Clinical Knowledge Sections (mirror PatientRecord) ───
    # Section 1: Demographics & identifiers
    patient_details: Optional[PatientDetails] = None

    # Section 2: Admission context
    admission_details: Optional[AdmissionDetails] = None

    # Section 3: All diagnostic findings
    diagnoses: List[Diagnosis] = Field(default_factory=list)

    # Section 4: Surgical / interventional procedures
    procedures: List[Procedure] = Field(default_factory=list)

    # Section 5: Labs, radiology, pathology
    investigations: List[Investigation] = Field(default_factory=list)

    # Section 6: Medication lifecycle
    medications: List[Medication] = Field(default_factory=list)

    # Section 7: Narrative timeline of the hospitalization
    hospital_course: Optional[HospitalCourse] = None

    # Section 8: Condition at discharge
    discharge_status: Optional[DischargeStatus] = None

    # Section 9: Post-discharge plan
    follow_up: Optional[FollowUp] = None

    # Section 10: Clinical & data quality flags
    flags: List[Flag] = Field(default_factory=list)

    # ── Reasoning-Only Sections ──────────────────────────────
    # Section 11: Unresolved contradictions between sources
    conflicts: List[Conflict] = Field(default_factory=list)

    # Section 12: Per-section readiness map for planner queries
    completeness_tracker: Dict[str, SectionStatus] = Field(
        default_factory=lambda: {
            "patient_details": SectionStatus(),
            "admission_details": SectionStatus(),
            "diagnoses": SectionStatus(),
            "procedures": SectionStatus(),
            "investigations": SectionStatus(),
            "medications": SectionStatus(),
            "hospital_course": SectionStatus(),
            "discharge_status": SectionStatus(),
            "follow_up": SectionStatus(),
            "flags": SectionStatus(),
        },
        description="Planner-readable map of section completeness"
    )

    # ── Query Helpers ────────────────────────────────────────

    def get_missing_sections(self) -> List[str]:
        """Return section names that are still empty."""
        return [
            name for name, status in self.completeness_tracker.items()
            if status.status == SectionStatusValue.EMPTY
        ]

    def get_partial_sections(self) -> List[str]:
        """Return section names that have partial data."""
        return [
            name for name, status in self.completeness_tracker.items()
            if status.status == SectionStatusValue.PARTIAL
        ]

    def get_unresolved_conflicts(self) -> List[Conflict]:
        """Return all conflicts that have not been resolved."""
        return [
            c for c in self.conflicts
            if c.resolution_status == ResolutionStatus.UNRESOLVED
        ]

    def get_low_confidence_items(
        self, threshold: float = 0.5
    ) -> Dict[str, list]:
        """
        Scan all clinical sections and return items whose confidence
        score falls below the given threshold.

        Returns a dict keyed by section name, each containing a list
        of (index, item) tuples.
        """
        results: Dict[str, list] = {}
        list_sections = {
            "diagnoses": self.diagnoses,
            "procedures": self.procedures,
            "investigations": self.investigations,
            "medications": self.medications,
        }
        for section_name, items in list_sections.items():
            weak = [
                (i, item) for i, item in enumerate(items)
                if item.confidence
                and item.confidence.confidence_score < threshold
            ]
            if weak:
                results[section_name] = weak

        # Check singleton sections that inherit ClinicalBase
        for section_name in [
            "patient_details", "admission_details", "hospital_course",
            "discharge_status", "follow_up",
        ]:
            item = getattr(self, section_name)
            if (
                item is not None
                and item.confidence
                and item.confidence.confidence_score < threshold
            ):
                results[section_name] = [(0, item)]

        return results
