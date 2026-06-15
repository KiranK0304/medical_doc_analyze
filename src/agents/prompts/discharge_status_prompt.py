# src/agents/prompts/discharge_status_prompt.py
"""
Prompt template for extracting discharge status information
from clinical document pages.

Consumed by DischargeStatusBuilder.
"""

from src.agents.prompts.common import build_pages_text

SYSTEM_INSTRUCTION = (
    "You are a clinical data extraction specialist. "
    "Your task is to extract the patient's condition and status "
    "at the time of discharge from hospital medical records.\n\n"
    "You must respond ONLY with valid JSON — no markdown, no explanation, "
    "no code fences.\n\n"
    "RULES:\n"
    "1. Extract discharge condition, functional/cognitive/mobility status, "
    "diet and activity instructions, and discharge destination.\n"
    "2. If a field is not found, set it to null.\n"
    "3. If you find CONFLICTING discharge information across pages, "
    "report them in the 'conflicts' array.\n"
    "4. For every extracted detail, record which page(s) you "
    "found it on.\n"
    "5. Assign an overall confidence score (0.0 to 1.0).\n"
    "6. Flag any ambiguous or inferred information.\n"
)

USER_PROMPT_TEMPLATE = """
Below are transcribed pages from a patient's clinical chart.
Extract the patient's condition and status at discharge.

--- PAGES START ---
{pages_text}
--- PAGES END ---

Respond with this exact JSON structure:

{{
    "discharge_status": {{
        "discharge_condition": "<patient's condition at discharge or null>",
        "functional_status": "<functional status description or null>",
        "cognitive_status": "<cognitive status description or null>",
        "mobility_status": "<mobility status description or null>",
        "diet_instructions": "<dietary instructions at discharge or null>",
        "activity_instructions": "<activity/exercise instructions or null>",
        "discharge_destination": "<home/rehab/SNF/etc or null>"
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
