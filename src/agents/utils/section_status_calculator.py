# src/agents/utils/section_status_calculator.py
"""
Computes a SectionStatus from any Pydantic model by checking which
fields among a given 'required' list are populated vs null/empty.

Works for every clinical section — just pass in the model instance
and the list of field names you consider required.
"""

from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel
from src.schemas.state import SectionStatus, SectionStatusValue


def compute_section_status(
    model_instance: Optional[BaseModel],
    required_fields: list[str],
    builder_name: str = "unknown_builder",
    notes: Optional[str] = None,
) -> SectionStatus:
    """
    Evaluate how complete a clinical section is.

    Args:
        model_instance: The Pydantic model instance to inspect
                        (e.g. a PatientDetails object). May be None
                        if nothing was extracted at all.
        required_fields: Field names that must be populated for the
                         section to be considered 'complete'.
        builder_name: Name of the builder/agent performing this check.
        notes: Optional free-form commentary.

    Returns:
        A SectionStatus with the correct status level and missing
        field list.
    """
    if model_instance is None:
        return SectionStatus(
            status=SectionStatusValue.EMPTY,
            missing_fields=required_fields.copy(),
            last_updated_by=builder_name,
            last_updated_at=datetime.now(timezone.utc),
            notes=notes or "No data extracted for this section.",
        )

    missing = []
    for field_name in required_fields:
        value = getattr(model_instance, field_name, None)
        if value is None:
            missing.append(field_name)
        elif isinstance(value, (list, dict)) and len(value) == 0:
            missing.append(field_name)
        elif isinstance(value, str) and value.strip() == "":
            missing.append(field_name)

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
