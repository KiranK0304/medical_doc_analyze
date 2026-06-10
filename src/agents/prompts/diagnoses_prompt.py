# src/agents/prompts/diagnoses_prompt.py
"""
Prompt template for extracting diagnoses from clinical document pages.

Consumed by DiagnosesBuilder.
"""

from src.agents.prompts.common import build_pages_text

SYSTEM_INSTRUCTION = (
    "You are a clinical data extraction specialist. "
    "Your task is to extract ALL diagnoses mentioned in hospital "
    "medical records.\n\n"
    "You must respond ONLY with valid JSON — no markdown, no explanation, "
    "no code fences.\n\n"
    "RULES:\n"
    "1. Extract EVERY diagnosis mentioned anywhere in the chart — "
    "admission diagnoses, discharge diagnoses, comorbidities, "
    "and historical conditions.\n"
    "2. Classify each diagnosis:\n"
    "   - type: primary | secondary | comorbidity | discharge\n"
    "   - status: active | resolved | suspected | historical | unknown\n"
    "3. If a diagnosis code (ICD-10 or similar) is present, include it.\n"
    "4. Dates should be in YYYY-MM-DD format when available.\n"
    "5. If a field is not found, set it to null.\n"
    "6. If you find CONFLICTING diagnosis information across pages "
    "(e.g. different primary diagnosis on different pages), report "
    "them in the 'conflicts' array.\n"
    "7. For every extracted diagnosis, record which page(s) you "
    "found it on.\n"
    "8. Assign an overall confidence score (0.0 to 1.0).\n"
    "9. Flag any ambiguous, partially legible, or inferred diagnoses.\n"
)

USER_PROMPT_TEMPLATE = """
Below are transcribed pages from a patient's clinical chart.
Extract ALL diagnoses mentioned anywhere in the document.

--- PAGES START ---
{pages_text}
--- PAGES END ---

Respond with this exact JSON structure:

{{
    "diagnoses": [
        {{
            "diagnosis_name": "<name of the diagnosis>",
            "diagnosis_code": "<ICD code or null>",
            "diagnosis_type": "<primary | secondary | comorbidity | discharge>",
            "diagnosis_status": "<active | resolved | suspected | historical | unknown>",
            "diagnosis_date": "<YYYY-MM-DD or null>",
            "notes": "<any relevant notes or null>"
        }}
    ],
    "evidence": [
        {{
            "field_name": "<which diagnosis this evidence supports>",
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
            "field_name": "<diagnosis with issue>",
            "issue": "<what is wrong>",
            "severity": "<low/medium/high/critical>"
        }}
    ],
    "conflicts": [
        {{
            "field_name": "<which diagnosis field has conflicting values>",
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


def build_user_prompt(extraction_json: dict) -> str:
    """
    Builds the full user prompt by inserting the concatenated pages
    into the prompt template.
    """
    pages_text = build_pages_text(extraction_json)
    return USER_PROMPT_TEMPLATE.format(pages_text=pages_text)
