# src/storage/json_writer.py
import json
from pathlib import Path

def save_extraction_data(filename: str, data: dict, output_dir: Path):
    """
    Accepts extracted VLM dictionary data and writes it cleanly 
    to the designated storage directory.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    target_path = output_dir / f"{Path(filename).stem}_extracted.json"
    
    with open(target_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
        
    print(f"🎉 Success! Structured file saved to storage: {target_path}")
    return target_path