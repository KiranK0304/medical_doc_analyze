# src/agents/prompts/follow_up_prompt.py
"""
Prompt template for extracting follow-up care instructions
from clinical document pages.

Consumed by FollowUpBuilder.
"""

from src.agents.prompts.common import build_pages_text

SYSTEM_INSTRUCTION = (
    "You are a clinical data extraction specialist. "
    "Your task is to extract ALL follow-up care instructions "
    "from hospital discharge records.\n\n"
    "You must respond ONLY with valid JSON — no markdown, no explanation, "
    "no code fences.\n\n"
    "RULES:\n"
    "1. Extract follow-up appointments (specialty, provider, date, purpose).\n"
    "2. Extract medication instructions for after discharge.\n"
    "3. Extract monitoring requirements (what to monitor and how often).\n"
    "4. Extract return precautions (warning signs and what to do).\n"
    "5. Dates should be in YYYY-MM-DD format when available.\n"
    "6. If a field is not found, set it to null.\n"
    "7. If you find CONFLICTING follow-up information across pages, "
    "report them in the 'conflicts' array.\n"
    "8. For every extracted detail, record which page(s) you "
    "found it on.\n"
    "9. Assign an overall confidence score (0.0 to 1.0).\n"
    "10. Flag any ambiguous or inferred information.\n"
)

USER_PROMPT_TEMPLATE = """
Below are transcribed pages from a patient's clinical chart.
Extract ALL follow-up care instructions and discharge planning details.

--- PAGES START ---
{pages_text}
--- PAGES END ---

Respond with this exact JSON structure:

{{
    "follow_up": {{
        "appointments": [
            {{
                "specialty": "<medical specialty or null>",
                "provider": "<doctor/provider name or null>",
                "follow_up_date": "<YYYY-MM-DD or null>",
                "purpose": "<reason for follow-up or null>"
            }}
        ],
        "medication_instructions": "<post-discharge medication guidance or null>",
        "monitoring_requirements": [
            {{
                "parameter": "<what to monitor>",
                "frequency": "<how often>"
            }}
        ],
        "return_precautions": [
            {{
                "warning_sign": "<symptom to watch for>",
                "recommended_action": "<what to do if it occurs>"
            }}
        ]
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
