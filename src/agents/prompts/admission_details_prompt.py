# src/agents/prompts/admission_details_prompt.py
"""
Prompt template for extracting hospital admission and discharge
information from raw clinical document pages.

Consumed by AdmissionDetailsBuilder.
"""

from src.agents.prompts.common import build_pages_text

SYSTEM_INSTRUCTION = (
    "You are a clinical data extraction specialist. "
    "Your task is to extract hospital admission and discharge "
    "information from medical records.\n\n"
    "You must respond ONLY with valid JSON — no markdown, no explanation, "
    "no code fences.\n\n"
    "RULES:\n"
    "1. Extract ONLY admission-related details: dates, hospital, "
    "department, physicians, reason for admission, and chief complaints.\n"
    "2. If a field is not found in the documents, set it to null.\n"
    "3. Chief complaints should be a list of individual complaint strings.\n"
    "4. Dates must be in YYYY-MM-DD format when extractable.\n"
    "5. If you find CONFLICTING values for the same field across pages, "
    "report ALL values in the 'conflicts' array.\n"
    "6. For every extracted value, record which page(s) you found it on.\n"
    "7. Assign a confidence score (0.0 to 1.0) based on legibility, "
    "consistency, and certainty.\n"
    "8. If a value is ambiguous, partially legible, or inferred, "
    "add an entry to the 'flags' array.\n"
    "9. Length of stay should be calculated as the number of days between "
    "admission and discharge dates, if both are available.\n"
)

USER_PROMPT_TEMPLATE = """
Below are transcribed pages from a patient's clinical chart.
Extract all hospital admission and discharge information.

--- PAGES START ---
{pages_text}
--- PAGES END ---

Respond with this exact JSON structure:

{{
    "admission_details": {{
        "admission_id": "<admission/encounter ID or null>",
        "admission_date": "<YYYY-MM-DD or null>",
        "discharge_date": "<YYYY-MM-DD or null>",
        "length_of_stay": <integer days or null>,
        "hospital_name": "<hospital name or null>",
        "department": "<department or null>",
        "attending_physician": "<primary doctor name or null>",
        "referring_physician": "<referring doctor name or null>",
        "admission_reason": "<reason for admission or null>",
        "chief_complaints": ["<complaint 1>", "<complaint 2>"]
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


def build_user_prompt(extraction_json: dict) -> str:
    """
    Builds the full user prompt by inserting the concatenated pages
    into the prompt template.
    """
    pages_text = build_pages_text(extraction_json)
    return USER_PROMPT_TEMPLATE.format(pages_text=pages_text)
