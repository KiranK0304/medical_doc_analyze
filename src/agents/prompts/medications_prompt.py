# src/agents/prompts/medications_prompt.py
"""
Prompt template for extracting medications from clinical document pages.

Consumed by MedicationsBuilder.
"""

from src.agents.prompts.common import build_pages_text

SYSTEM_INSTRUCTION = (
    "You are a clinical data extraction specialist. "
    "Your task is to extract ALL medications mentioned in hospital "
    "medical records.\n\n"
    "You must respond ONLY with valid JSON — no markdown, no explanation, "
    "no code fences.\n\n"
    "RULES:\n"
    "1. Extract EVERY medication mentioned — current medications, "
    "newly prescribed, modified, stopped, and discharge medications.\n"
    "2. Include dose, unit, frequency, and route when available.\n"
    "3. Classify each medication's status: "
    "started | continued | modified | stopped | completed | unknown.\n"
    "4. Include generic name if it differs from the brand name.\n"
    "5. Dates should be in YYYY-MM-DD format when available.\n"
    "6. If a field is not found, set it to null.\n"
    "7. If you find CONFLICTING medication information across pages "
    "(e.g. different doses on different pages), report them in the "
    "'conflicts' array.\n"
    "8. For every extracted medication, record which page(s) you "
    "found it on.\n"
    "9. Assign an overall confidence score (0.0 to 1.0).\n"
    "10. Flag any ambiguous, partially legible, or inferred medications.\n"
)

USER_PROMPT_TEMPLATE = """
Below are transcribed pages from a patient's clinical chart.
Extract ALL medications mentioned anywhere in the document.

--- PAGES START ---
{pages_text}
--- PAGES END ---

Respond with this exact JSON structure:

{{
    "medications": [
        {{
            "medication_name": "<brand or generic name>",
            "generic_name": "<generic name if different from medication_name, or null>",
            "dose": "<dose amount or null>",
            "dosage_unit": "<mg/ml/units/etc or null>",
            "frequency": "<e.g. BD, TDS, OD, PRN, or null>",
            "route": "<oral/IV/IM/SC/topical/etc or null>",
            "indication": "<reason for prescribing or null>",
            "start_date": "<YYYY-MM-DD or null>",
            "end_date": "<YYYY-MM-DD or null>",
            "status": "<started | continued | modified | stopped | completed | unknown>"
        }}
    ],
    "evidence": [
        {{
            "field_name": "<which medication this evidence supports>",
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
            "field_name": "<medication with issue>",
            "issue": "<what is wrong>",
            "severity": "<low/medium/high/critical>"
        }}
    ],
    "conflicts": [
        {{
            "field_name": "<which medication field has conflicting values>",
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
