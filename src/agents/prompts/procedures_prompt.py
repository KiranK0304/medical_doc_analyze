# src/agents/prompts/procedures_prompt.py
"""
Prompt template for extracting procedures from clinical document pages.

Consumed by ProceduresBuilder.
"""

from src.agents.prompts.common import build_pages_text

SYSTEM_INSTRUCTION = (
    "You are a clinical data extraction specialist. "
    "Your task is to extract ALL procedures and interventions "
    "mentioned in hospital medical records.\n\n"
    "You must respond ONLY with valid JSON — no markdown, no explanation, "
    "no code fences.\n\n"
    "RULES:\n"
    "1. Extract EVERY procedure mentioned anywhere in the chart — "
    "surgical procedures, diagnostic procedures, therapeutic interventions, "
    "and bedside procedures.\n"
    "2. If a procedure code (CPT, SNOMED, or similar) is present, include it.\n"
    "3. Dates should be in YYYY-MM-DD format when available.\n"
    "4. If a field is not found, set it to null.\n"
    "5. If you find CONFLICTING procedure information across pages, "
    "report them in the 'conflicts' array.\n"
    "6. For every extracted procedure, record which page(s) you "
    "found it on.\n"
    "7. Assign an overall confidence score (0.0 to 1.0).\n"
    "8. Flag any ambiguous, partially legible, or inferred procedures.\n"
)

USER_PROMPT_TEMPLATE = """
Below are transcribed pages from a patient's clinical chart.
Extract ALL procedures and interventions mentioned anywhere in the document.

--- PAGES START ---
{pages_text}
--- PAGES END ---

Respond with this exact JSON structure:

{{
    "procedures": [
        {{
            "procedure_name": "<name of the procedure>",
            "procedure_code": "<CPT/SNOMED code or null>",
            "procedure_date": "<YYYY-MM-DD or null>",
            "indication": "<reason the procedure was performed or null>",
            "outcome": "<result/outcome or null>",
            "performing_department": "<department that performed it or null>",
            "notes": "<any relevant notes or null>"
        }}
    ],
    "evidence": [
        {{
            "field_name": "<which procedure this evidence supports>",
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
            "field_name": "<procedure with issue>",
            "issue": "<what is wrong>",
            "severity": "<low/medium/high/critical>"
        }}
    ],
    "conflicts": [
        {{
            "field_name": "<which procedure field has conflicting values>",
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
