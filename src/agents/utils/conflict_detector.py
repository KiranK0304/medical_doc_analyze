# src/agents/utils/conflict_detector.py
"""
Reusable conflict-detection helper.

Given the 'conflicts' array from an LLM response, this module
creates proper Conflict and CompetingValue schema objects.

The same logic applies to every builder (patient_details, diagnosis,
medications, etc.), so it lives here as a shared utility.
"""

import uuid
from datetime import datetime, timezone

from src.schemas.base import Evidence, Confidence
from src.schemas.state import Conflict, CompetingValue, ResolutionStatus


def build_conflicts_from_llm_response(
    conflict_entries: list[dict],
    section: str,
    source_document: str,
) -> list[Conflict]:
    """
    Convert the raw 'conflicts' array from the LLM JSON into a list
    of Conflict schema objects.

    Args:
        conflict_entries: List of dicts from the LLM, each containing
                          'field_name' and 'values' (list of competing
                          value dicts with 'value', 'page_number',
                          'extracted_text').
        section: The ClinicalState section name (e.g. 'patient_details').
        source_document: The source document identifier.

    Returns:
        List of fully constructed Conflict objects ready to be appended
        to ClinicalState.conflicts.
    """
    conflicts: list[Conflict] = []

    for entry in conflict_entries:
        field_name = entry.get("field_name", "unknown")
        raw_values = entry.get("values", [])

        if len(raw_values) < 2:
            # A conflict needs at least two sides
            continue

        competing = []
        for rv in raw_values:
            evidence = Evidence(
                source_document=source_document,
                page_number=rv.get("page_number"),
                extracted_text=rv.get("extracted_text", ""),
            )
            confidence = None
            if rv.get("confidence_score") is not None:
                confidence = Confidence(
                    confidence_score=rv["confidence_score"],
                    confidence_reason=rv.get("confidence_reason"),
                )

            competing.append(
                CompetingValue(
                    value=rv.get("value"),
                    evidence=evidence,
                    confidence=confidence,
                )
            )

        conflicts.append(
            Conflict(
                conflict_id=str(uuid.uuid4()),
                section=section,
                field_path=f"{section}.{field_name}",
                competing_values=competing,
                resolution_status=ResolutionStatus.UNRESOLVED,
                detected_at=datetime.now(timezone.utc),
            )
        )

    return conflicts
