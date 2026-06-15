# src/agents/prompts/hospital_course_prompt.py
"""
Prompt template for extracting hospital course information
from clinical document pages.

Consumed by HospitalCourseBuilder.
"""

from src.agents.prompts.common import build_pages_text

SYSTEM_INSTRUCTION = (
    "You are a clinical data extraction specialist. "
    "Your task is to extract the hospital course narrative and "
    "key clinical events from hospital medical records.\n\n"
    "You must respond ONLY with valid JSON — no markdown, no explanation, "
    "no code fences.\n\n"
    "RULES:\n"
    "1. Summarise the admission narrative, key clinical events, "
    "complications, treatment response, and discharge summary.\n"
    "2. Key clinical events should be a list of timestamped events "
    "in chronological order.\n"
    "3. Timestamps should be in ISO 8601 format (YYYY-MM-DDTHH:MM:SS) "
    "when time is available, or YYYY-MM-DDT00:00:00 when only a date "
    "is known.\n"
    "4. If a field is not found, set it to null.\n"
    "5. If you find CONFLICTING information about the clinical course "
    "across pages, report them in the 'conflicts' array.\n"
    "6. For every extracted detail, record which page(s) you "
    "found it on.\n"
    "7. Assign an overall confidence score (0.0 to 1.0).\n"
    "8. Flag any ambiguous or inferred information.\n"
)

USER_PROMPT_TEMPLATE = """
Below are transcribed pages from a patient's clinical chart.
Extract the hospital course — the narrative of what happened during
the patient's stay.

--- PAGES START ---
{pages_text}
--- PAGES END ---

Respond with this exact JSON structure:

{{
    "hospital_course": {{
        "admission_summary": "<brief summary of the admission or null>",
        "key_clinical_events": [
            {{
                "timestamp": "<YYYY-MM-DDTHH:MM:SS>",
                "description": "<what happened>"
            }}
        ],
        "complications": "<any complications or null>",
        "treatment_response": "<how the patient responded to treatment or null>",
        "discharge_summary": "<brief discharge summary or null>"
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
