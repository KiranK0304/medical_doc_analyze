# src/agents/utils/evidence_factory.py
"""
Helpers for creating Evidence objects from LLM responses.

Every builder needs to convert raw page references into proper
Evidence instances. This module avoids copy-pasting that logic.
"""

from src.schemas.base import Evidence


def create_evidence(
    source_document: str,
    page_number: int | None,
    extracted_text: str,
    section_name: str | None = None,
) -> Evidence:
    """
    Build a single Evidence object from extraction metadata.

    Args:
        source_document: Filename or identifier of the source PDF.
        page_number: Page where the information was found.
        extracted_text: Raw text snippet that backs the extracted value.
        section_name: Optional logical section name within the document.

    Returns:
        A fully populated Evidence instance.
    """
    return Evidence(
        source_document=source_document,
        page_number=page_number,
        extracted_text=extracted_text,
        section_name=section_name,
    )


def create_evidence_list_from_llm_response(
    evidence_entries: list[dict],
    source_document: str,
) -> dict[str, list[Evidence]]:
    """
    Convert the 'evidence' array from the LLM JSON response into a
    dict mapping field names to their Evidence lists.

    Args:
        evidence_entries: List of dicts, each with 'field_name',
                          'page_number', and 'extracted_text'.
        source_document: The source document identifier.

    Returns:
        Dict mapping field_name -> [Evidence, ...].
    """
    evidence_map: dict[str, list[Evidence]] = {}

    for entry in evidence_entries:
        field_name = entry.get("field_name", "unknown")
        ev = create_evidence(
            source_document=source_document,
            page_number=entry.get("page_number"),
            extracted_text=entry.get("extracted_text", ""),
            section_name=entry.get("section_name"),
        )
        evidence_map.setdefault(field_name, []).append(ev)

    return evidence_map
