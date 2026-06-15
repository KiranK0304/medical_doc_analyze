# src/agents/prompts/investigations_prompt.py
"""
Prompt template for extracting investigations (labs, radiology, etc.)
from clinical document pages.

Consumed by InvestigationsBuilder.
"""

from src.agents.prompts.common import build_pages_text

SYSTEM_INSTRUCTION = (
    "You are a clinical data extraction specialist. "
    "Your task is to extract ALL investigations and diagnostic tests "
    "mentioned in hospital medical records.\n\n"
    "You must respond ONLY with valid JSON — no markdown, no explanation, "
    "no code fences.\n\n"
    "RULES:\n"
    "1. Extract EVERY investigation mentioned — laboratory tests, "
    "radiology studies, pathology reports, microbiology cultures, "
    "cardiology tests (ECG, Echo), and any other diagnostic tests.\n"
    "2. Classify each investigation into a category: "
    "laboratory | radiology | pathology | microbiology | cardiology | other.\n"
    "3. Include results, normal ranges, and interpretations when available.\n"
    "4. Dates should be in YYYY-MM-DD format when available.\n"
    "5. If a field is not found, set it to null.\n"
    "6. If you find CONFLICTING results across pages, "
    "report them in the 'conflicts' array.\n"
    "7. For every extracted investigation, record which page(s) you "
    "found it on.\n"
    "8. Assign an overall confidence score (0.0 to 1.0).\n"
    "9. Flag any ambiguous, partially legible, or inferred results.\n"
)

USER_PROMPT_TEMPLATE = """
Below are transcribed pages from a patient's clinical chart.
Extract ALL investigations and diagnostic tests mentioned anywhere.

--- PAGES START ---
{pages_text}
--- PAGES END ---

Respond with this exact JSON structure:

{{
    "investigations": [
        {{
            "investigation_name": "<name of the test>",
            "category": "<laboratory | radiology | pathology | microbiology | cardiology | other>",
            "result": "<test result or null>",
            "normal_range": "<reference range or null>",
            "interpretation": "<normal/abnormal/critical interpretation or null>",
            "investigation_date": "<YYYY-MM-DD or null>"
        }}
    ],
    "evidence": [
        {{
            "field_name": "<which investigation this evidence supports>",
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
            "field_name": "<investigation with issue>",
            "issue": "<what is wrong>",
            "severity": "<low/medium/high/critical>"
        }}
    ],
    "conflicts": [
        {{
            "field_name": "<which investigation field has conflicting values>",
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
