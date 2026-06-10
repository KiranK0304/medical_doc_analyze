# src/agents/utils/section_status_calculator.py
"""
Computes a SectionStatus from any Pydantic model (or list of models)
by checking which fields among a given 'required' list are populated
vs null/empty.

Handles two patterns:
    - Singleton sections (PatientDetails, AdmissionDetails, etc.)
    - List sections (List[Diagnosis], List[Medication], etc.)
"""

from datetime import datetime, timezone
from typing import Optional, Union

from pydantic import BaseModel
from src.schemas.state import SectionStatus, SectionStatusValue


def _is_field_populated(value) -> bool:
    """Return True if a field value counts as 'present'."""
    if value is None:
        return False
    if isinstance(value, (list, dict)) and len(value) == 0:
        return False
    if isinstance(value, str) and value.strip() == "":
        return False
    return True


def _check_single_model(
    model_instance: BaseModel,
    required_fields: list[str],
) -> list[str]:
    """Return list of missing required field names on a single model."""
    return [
        f for f in required_fields
        if not _is_field_populated(getattr(model_instance, f, None))
    ]


def compute_section_status(
    model_instance: Optional[Union[BaseModel, list]],
    required_fields: list[str],
    builder_name: str = "unknown_builder",
    notes: Optional[str] = None,
) -> SectionStatus:
    """
    Evaluate how complete a clinical section is.

    Args:
        model_instance: Either a single Pydantic model (for singleton
                        sections like PatientDetails), a list of models
                        (for list sections like diagnoses), or None.
        required_fields: Field names that must be populated for the
                         section to be considered 'complete'.
        builder_name: Name of the builder/agent performing this check.
        notes: Optional free-form commentary.

    Returns:
        A SectionStatus with the correct status level and missing
        field list.
    """

    # ── Nothing extracted at all ─────────────────────────────
    if model_instance is None:
        return SectionStatus(
            status=SectionStatusValue.EMPTY,
            missing_fields=required_fields.copy(),
            last_updated_by=builder_name,
            last_updated_at=datetime.now(timezone.utc),
            notes=notes or "No data extracted for this section.",
        )

    # ── List-based sections (diagnoses, medications, etc.) ───
    if isinstance(model_instance, list):
        return _compute_list_status(
            model_instance, required_fields, builder_name, notes
        )

    # ── Singleton sections (patient_details, etc.) ───────────
    missing = _check_single_model(model_instance, required_fields)

    if len(missing) == len(required_fields):
        status = SectionStatusValue.EMPTY
    elif len(missing) > 0:
        status = SectionStatusValue.PARTIAL
    else:
        status = SectionStatusValue.COMPLETE

    return SectionStatus(
        status=status,
        missing_fields=missing,
        last_updated_by=builder_name,
        last_updated_at=datetime.now(timezone.utc),
        notes=notes,
    )


def _compute_list_status(
    items: list,
    required_fields: list[str],
    builder_name: str,
    notes: Optional[str],
) -> SectionStatus:
    """
    Compute status for a list-based section.

    - Empty list       → EMPTY
    - All items fully populated → COMPLETE
    - Otherwise        → PARTIAL, with missing fields annotated
                          as "item[i].field_name" so you know which
                          item has the gap.
    """
    if len(items) == 0:
        return SectionStatus(
            status=SectionStatusValue.EMPTY,
            missing_fields=required_fields.copy(),
            last_updated_by=builder_name,
            last_updated_at=datetime.now(timezone.utc),
            notes=notes or "No items extracted for this section.",
        )

    all_missing: list[str] = []
    for idx, item in enumerate(items):
        for field_name in required_fields:
            if not _is_field_populated(getattr(item, field_name, None)):
                all_missing.append(f"item[{idx}].{field_name}")

    if len(all_missing) == 0:
        status = SectionStatusValue.COMPLETE
    else:
        status = SectionStatusValue.PARTIAL

    return SectionStatus(
        status=status,
        missing_fields=all_missing,
        last_updated_by=builder_name,
        last_updated_at=datetime.now(timezone.utc),
        notes=notes,
    )
