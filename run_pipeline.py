# run_pipeline.py
"""
End-to-end pipeline for clinical document analysis.

Phase 1: PDF → page images
Phase 2: Images → extraction JSON (VLM transcription)
Phase 3: Save extraction JSON
Phase 4: Extraction JSON → ClinicalState (orchestrator + 9 builders)
Phase 5: ClinicalState → PatientRecord → save final JSON
"""

import os
import json
import time
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Explicitly import modular code from your project structure folders
from src.extraction.pdf_processor import split_pdf_to_pngs
from src.extraction.vlm_extractor import extract_text_from_images
from src.storage.json_writer import save_extraction_data
from src.agents.orchestrator import build_clinical_state
from src.agents.synthesizer import synthesize_patient_record


# Define the data directory path
DATA_DIR = Path(__file__).parent / "data"

# Automatically create the folder if it does not exist
DATA_DIR.mkdir(parents=True, exist_ok=True)

API_KEY = os.getenv("GEMINI_API_KEY")
TARGET_PDF_NAME = "clinical_chart.pdf"  # Put this file in data/raw_pdfs/

# Setup directory maps natively using clean Path structures
BASE_DIR = Path(__file__).parent
RAW_PDF_DIR = BASE_DIR / "data" / "raw_pdfs"
INTERIM_IMG_DIR = BASE_DIR / "data" / "interim_images"
STRUCTURED_JSON_DIR = BASE_DIR / "data" / "structured_json"

def main():
    if not API_KEY:
        print("❌ Aborting. GEMINI_API_KEY not found in environment or .env file.")
        return

    target_pdf_path = RAW_PDF_DIR / TARGET_PDF_NAME
    
    if not target_pdf_path.exists():
        print(f"❌ Aborting. Please place your file inside: {target_pdf_path}")
        return

    pipeline_start = time.time()

    # ── Phase 1: Split PDF into page images ──────────────────
    print("\n📋 Phase 1: Splitting PDF into page images...")
    cached_images = split_pdf_to_pngs(
        pdf_path=target_pdf_path, 
        output_img_dir=INTERIM_IMG_DIR, 
        max_pages=100
    )
    
    # ── Phase 2: VLM transcription ───────────────────────────
    print("\n🔍 Phase 2: Transcribing page images with VLM...")
    extracted_dictionary = extract_text_from_images(
        image_paths=cached_images, 
        api_key=API_KEY, 
        delay_seconds=10.0  # Keeps us safely under the limits
    )
    
    # ── Phase 3: Save raw extraction JSON ────────────────────
    print("\n💾 Phase 3: Saving extraction JSON...")
    extraction_path = save_extraction_data(
        filename=TARGET_PDF_NAME, 
        data=extracted_dictionary, 
        output_dir=STRUCTURED_JSON_DIR
    )

    # ── Phase 4: Run orchestrator (extraction → ClinicalState) ─
    print("\n🧠 Phase 4: Running clinical extraction builders...")
    clinical_state = build_clinical_state(
        extraction_json=extracted_dictionary,
        api_key=API_KEY,
        source_document=TARGET_PDF_NAME,
        case_id=Path(TARGET_PDF_NAME).stem,
    )

    # ── Phase 5: Synthesize PatientRecord and save ───────────
    print("\n📝 Phase 5: Synthesizing final PatientRecord...")
    pipeline_duration = time.time() - pipeline_start

    patient_record = synthesize_patient_record(
        state=clinical_state,
        source_page_count=len(cached_images),
        processing_duration=pipeline_duration,
    )

    # Save the final patient record as JSON
    output_path = STRUCTURED_JSON_DIR / f"{Path(TARGET_PDF_NAME).stem}_patient_record.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(
            patient_record.model_dump(mode="json"),
            f,
            indent=4,
            ensure_ascii=False,
            default=str,  # handles date/datetime serialisation
        )

    print(f"\n🎉 Pipeline complete! ({pipeline_duration:.1f}s)")
    print(f"   Extraction JSON: {extraction_path}")
    print(f"   Patient Record:  {output_path}")

if __name__ == "__main__":
    main()