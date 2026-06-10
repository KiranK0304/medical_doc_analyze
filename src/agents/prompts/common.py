# src/agents/prompts/common.py
"""
Shared prompt utilities used by all section-specific prompt modules.
"""


def build_pages_text(extraction_json: dict) -> str:
    """
    Concatenates all successful page transcriptions into a single
    text block for the LLM prompt, clearly marking page boundaries.

    This is used by every section builder's prompt, so it lives
    here rather than in a section-specific module.
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
