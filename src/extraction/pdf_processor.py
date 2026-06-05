# src/extraction/pdf_processor.py
import os
from pathlib import Path
from pdf2image import convert_from_path

def split_pdf_to_pngs(pdf_path: Path, output_img_dir: Path, max_pages: int = 20) -> list[Path]:
    """
    Takes a multi-page clinical PDF, extracts up to max_pages, 
    and saves them as sequential image assets.
    """
    doc_id = pdf_path.stem
    target_sub_dir = output_img_dir / doc_id
    target_sub_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"📋 Slicing top {max_pages} pages from: {pdf_path.name}...")
    
    # Extract only the specified testing page subset range
    pages = convert_from_path(pdf_path, dpi=200, first_page=1, last_page=max_pages)
    
    image_paths = []
    for idx, page in enumerate(pages, start=1):
        img_file_path = target_sub_dir / f"page_{idx}.png"
        page.save(img_file_path, "PNG")
        image_paths.append(img_file_path)
        
    print(f"💾 Rendered {len(image_paths)} pages locally inside: {target_sub_dir}")
    return image_paths