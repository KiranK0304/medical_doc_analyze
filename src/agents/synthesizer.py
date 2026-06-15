# src/agents/synthesizer.py
"""
Synthesizer — converts ClinicalState into a final PatientRecord.

Since ClinicalState and PatientRecord share the same field names and
Pydantic models, this is a shallow copy — zero LLM calls needed.

The only real work is:
    1. Copy the 10 clinical sections over
    2. Convert unresolved conflicts into Flag entries
    3. Build the evidence_map and confidence_metadata from section models
    4. Populate ProcessingMetadata

Usage:
    from src.agents.synthesizer import synthesize_patient_record

    record = synthesize_patient_record(
        state=clinical_state,
        source_page_count=15,
        processing_duration=42.5,
    )
"""

from datetime import datetime, timezone
from typing import Dict, List

from src.schemas.base import Confidence, Evidence, Flag, ReviewItem, Severity
from src.schemas.record import PatientRecord, ProcessingMetadata
from src.schemas.state import ClinicalState, ResolutionStatus


def synthesize_patient_record(
    state: ClinicalState,
    source_page_count: int = 0,
    processing_duration: float = 0.0,
    system_version: str = "0.1.0",
) -> PatientRecord:
    """
    Transform a ClinicalState into a PatientRecord.

    Args:
        state: The fully hydrated ClinicalState from the orchestrator.
        source_page_count: Number of pages in the source document.
        processing_duration: Total processing time in seconds.
        system_version: Version string for traceability.

    Returns:
        A PatientRecord ready for storage or downstream consumption.
    """

    # ── 1. Shallow-copy clinical sections ────────────────────
    record = PatientRecord(
        patient_details=state.patient_details,
        admission_details=state.admission_details,
        diagnoses=state.diagnoses,
        procedures=state.procedures,
        investigations=state.investigations,
        medications=state.medications,
        hospital_course=state.hospital_course,
        discharge_status=state.discharge_status,
        follow_up=state.follow_up,
        flags=list(state.flags),  # copy so mutations don't leak
    )

    # ── 2. Convert unresolved conflicts to flags ─────────────
    conflict_flags = _conflicts_to_flags(state)
    record.flags.extend(conflict_flags)

    # ── 3. Build evidence_map and confidence_metadata ────────
    record.evidence_map = _build_evidence_map(state)
    record.confidence_metadata = _build_confidence_metadata(state)

    # ── 4. Processing metadata ───────────────────────────────
    record.processing_metadata = ProcessingMetadata(
        processing_timestamp=datetime.now(timezone.utc),
        schema_version=state.schema_version,
        source_document_count=1,
        source_page_count=source_page_count,
        processing_duration_seconds=processing_duration,
        system_version=system_version,
    )

    return record


def _conflicts_to_flags(state: ClinicalState) -> List[Flag]:
    """
    Convert unresolved conflicts into Flag entries so they're
    visible in the final PatientRecord.
    """
    flags = []
    for conflict in state.conflicts:
        if conflict.resolution_status != ResolutionStatus.UNRESOLVED:
            continue

        values_summary = ", ".join(
            str(cv.value) for cv in conflict.competing_values
        )
        flags.append(
            Flag(
                flag_type="UnresolvedConflict",
                name=conflict.field_path,
                description=(
                    f"Unresolved conflict in {conflict.section}.{conflict.field_path}: "
                    f"competing values = [{values_summary}]"
                ),
                review_required=ReviewItem(
                    issue=f"Conflicting values for {conflict.field_path}",
                    reason=f"Found {len(conflict.competing_values)} competing values across source pages",
                    severity=Severity.HIGH,
                ),
            )
        )
    return flags


def _build_evidence_map(state: ClinicalState) -> Dict[str, List[Evidence]]:
    """
    Collect evidence lists from all clinical sections into a
    single dict keyed by section name.
    """
    evidence_map: Dict[str, List[Evidence]] = {}

    # Singleton sections
    for section_name in [
        "patient_details", "admission_details", "hospital_course",
        "discharge_status", "follow_up",
    ]:
        model = getattr(state, section_name, None)
        if model is not None and model.evidence:
            evidence_map[section_name] = list(model.evidence)

    # List sections
    for section_name in [
        "diagnoses", "procedures", "investigations", "medications",
    ]:
        items = getattr(state, section_name, [])
        section_evidence = []
        for item in items:
            if item.evidence:
                section_evidence.extend(item.evidence)
        if section_evidence:
            evidence_map[section_name] = section_evidence

    return evidence_map


def _build_confidence_metadata(
    state: ClinicalState,
) -> Dict[str, Confidence]:
    """
    Collect confidence scores from all sections into a
    single dict keyed by section name.
    """
    metadata: Dict[str, Confidence] = {}

    # Singleton sections
    for section_name in [
        "patient_details", "admission_details", "hospital_course",
        "discharge_status", "follow_up",
    ]:
        model = getattr(state, section_name, None)
        if model is not None and model.confidence:
            metadata[section_name] = model.confidence

    # List sections — average confidence across items
    for section_name in [
        "diagnoses", "procedures", "investigations", "medications",
    ]:
        items = getattr(state, section_name, [])
        scores = [
            item.confidence.confidence_score
            for item in items
            if item.confidence and item.confidence.confidence_score is not None
        ]
        if scores:
            avg = sum(scores) / len(scores)
            metadata[section_name] = Confidence(
                confidence_score=avg,
                confidence_reason=f"Average of {len(scores)} item confidence scores",
            )

    return metadata
