# src/extraction/vlm_extractor.py
import time
from pathlib import Path
from google import genai
from google.genai import types
from PIL import Image

# Your optimized system instruction focusing heavily on Markdown enforcement
SYSTEM_INSTRUCTION = (
    "You are an advanced clinical data extraction expert specializing in structured medical forms and charts.\n\n"
    "CRITICAL STRUCTURAL RULES:\n"
    "1. This document contains a multi-column structured table or flow sheet layout (containing headers like Date, Time, Observation, Nursing Action Plan, Staff Name, etc.).\n"
    "2. DO NOT read straight across the page horizontally if it mixes separate columns together. Group the information logically by row or by column section so the clinical context is preserved.\n"
    "3. Use your deep knowledge of medical charting vocabulary, shorthand, and metrics to clean up messy handwriting or low-resolution text. Never output nonsense character strings like 'Nsiiz' or 'b du-6999'. Convert them to their closest medical meaning based on context.\n"
    "4. Output the extracted data strictly in a beautifully formatted Markdown layout (using Markdown tables or clear headers/bullet points for each row entry).\n\n"
    "Output MUST be clean, coherent Markdown. Do not include conversational text or code block wrappers like ```markdown."
)

def extract_text_from_images(image_paths: list[Path], api_key: str, delay_seconds: float = 6.0) -> dict:
    """
    Iterates through image assets, communicates with the gemini-2.5-flash VLM, 
    and returns a structured payload containing markdown transcriptions.
    """
    client = genai.Client(api_key=api_key)
    
    compiled_payload = {
        "metadata": {
            "total_pages_processed": len(image_paths),
            "timestamp_extracted": time.strftime("%Y-%m-%d %H:%M:%S")
        },
        "pages": {}
    }

    print(f"🚀 Initializing VLM extraction pipeline with a {delay_seconds}s safety delay spacing...")

    for idx, path in enumerate(image_paths, start=1):
        print(f"🤖 Processing Page {idx}/{len(image_paths)} via Gemini...")
        img = Image.open(path)
        
        try:
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=[img, f"Extract and transcribe the text from this page following your strict Markdown structural rules. Page index: {idx}"],
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_INSTRUCTION
                )
            )
            
            compiled_payload["pages"][f"page_{idx}"] = {
                "page_number": idx,
                "status": "Success",
                "transcription": response.text  # This will now contain clean, robust Markdown string data
            }
            
        except Exception as e:
            print(f"⚠️ Error handling page {idx}: {e}")
            compiled_payload["pages"][f"page_{idx}"] = {
                "page_number": idx,
                "status": "Failed",
                "error": str(e)
            }
            
        # Pacing boundary check to protect free requests-per-minute thresholds
        if idx < len(image_paths):
            time.sleep(delay_seconds)
            
    return compiled_payload