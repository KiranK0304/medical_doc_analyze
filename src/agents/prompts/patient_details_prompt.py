# src/agents/prompts/patient_details_prompt.py
"""
Prompt template for extracting patient demographic information
from raw clinical document pages.

This prompt is consumed by PatientDetailsBuilder and sent to the LLM.
Keep all prompt text in this file so it can be iterated on independently
of the builder logic.
"""

SYSTEM_INSTRUCTION = (
    "You are a clinical data extraction specialist. "
    "Your task is to extract patient demographic and identification "
    "information from hospital medical records.\n\n"
    "You must respond ONLY with valid JSON — no markdown, no explanation, "
    "no code fences.\n\n"
    "RULES:\n"
    "1. Extract ONLY patient identification and demographic details.\n"
    "2. If a field is not found in the documents, set it to null.\n"
    "3. If you find CONFLICTING values for the same field across pages, "
    "report ALL values in the 'conflicts' array.\n"
    "4. For every extracted value, record which page(s) you found it on.\n"
    "5. Assign a confidence score (0.0 to 1.0) for each extracted value "
    "based on legibility, consistency, and certainty.\n"
    "6. If a value is ambiguous, partially legible, or inferred, "
    "add an entry to the 'flags' array.\n"
)

USER_PROMPT_TEMPLATE = """
Below are transcribed pages from a patient's clinical chart.
Extract all patient demographic and identification information.

--- PAGES START ---
{pages_text}
--- PAGES END ---

Respond with this exact JSON structure:

{{
    "patient_details": {{
        "patient_id": "<extracted ID or null>",
        "medical_record_number": "<MRN or null>",
        "patient_name": "<name or null>",
        "age": <integer or null>,
        "age_unit": "<years/months/days or null>",
        "gender": "<Male/Female/Other or null>",
        "date_of_birth": "<YYYY-MM-DD or null>",
        "address": "<address or null>",
        "contact_information": "<phone/email or null>"
    }},
    "evidence": [
        {{
            "field_name": "<which field this evidence supports>",
            "page_number": <int>,
            "extracted_text": "<exact text snippet from the page>"
        }}
    ],
    "confidence": {{
        "overall_score": <float 0.0-1.0>,
        "reason": "<why this confidence level>"
    }},
    "flags": [
        {{
            "field_name": "<field with issue>",
            "issue": "<what is wrong>",
            "severity": "<low/medium/high/critical>"
        }}
    ],
    "conflicts": [
        {{
            "field_name": "<field with conflicting values>",
            "values": [
                {{
                    "value": "<first value>",
                    "page_number": <int>,
                    "extracted_text": "<snippet>"
                }},
                {{
                    "value": "<second value>",
                    "page_number": <int>,
                    "extracted_text": "<snippet>"
                }}
            ]
        }}
    ]
}}
"""


def build_pages_text(extraction_json: dict) -> str:
    """
    Concatenates all successful page transcriptions into a single
    text block for the LLM prompt, clearly marking page boundaries.
    """
    parts = []
    pages = extraction_json.get("pages", {})

    for page_key in sorted(pages.keys(), key=lambda k: pages[k].get("page_number", 0)):
        page = pages[page_key]
        if page.get("status") == "Success" and page.get("transcription"):
            parts.append(
                f"=== PAGE {page['page_number']} ===\n"
                f"{page['transcription']}\n"
            )

    return "\n".join(parts)


def build_user_prompt(extraction_json: dict) -> str:
    """
    Builds the full user prompt by inserting the concatenated pages
    into the prompt template.
    """
    pages_text = build_pages_text(extraction_json)
    return USER_PROMPT_TEMPLATE.format(pages_text=pages_text)
