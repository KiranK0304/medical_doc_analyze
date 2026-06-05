# run_pipeline.py
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


# Explicitly import modular code from your project structure folders
from src.extraction.pdf_processor import split_pdf_to_pngs
from src.extraction.vlm_extractor import extract_text_from_images
from src.storage.json_writer import save_extraction_data


# Define the data directory path
DATA_DIR = Path(__file__).parent / "data"

# Automatically create the folder if it does not exist
DATA_DIR.mkdir(parents=True, exist_ok=True)

API_KEY = os.getenv("GEMINI_API_KEY")
TARGET_PDF_NAME = "clinical_chart.pdf"  # Put this file in data/01_raw_pdfs/

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
        
    # Phase 1: Call your Extraction module to split the multi-page PDF
    cached_images = split_pdf_to_pngs(
        pdf_path=target_pdf_path, 
        output_img_dir=INTERIM_IMG_DIR, 
        max_pages=100
    )
    
    # Phase 2: Call your Extraction VLM system loop to transcribe the items
    extracted_dictionary = extract_text_from_images(
        image_paths=cached_images, 
        api_key=API_KEY, 
        delay_seconds=10.0  # Keeps us safely under the limits
    )
    
    # Phase 3: Route the compiled structured output straight into Storage
    save_extraction_data(
        filename=TARGET_PDF_NAME, 
        data=extracted_dictionary, 
        output_dir=STRUCTURED_JSON_DIR
    )

if __name__ == "__main__":
    main()