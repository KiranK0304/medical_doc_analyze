# MDocAnalyzer

**Medical Document Analyzer** – a modular, agent‑driven platform for turning raw clinical PDFs into a structured, audit‑ready hospitalization summary.

---

## Project Vision

- **Goal**: Ingest multiple‑page clinical charts, extract high‑confidence clinical facts, reconcile conflicts, and output a canonical `PatientRecord` JSON schema.
- **Architecture**: 
  - **Extraction agents** read PDFs → produce raw markdown pages.
  - **Validation & Consensus agents** add evidence, confidence, and resolve contradictions.
  - **Planner agent** drives the workflow, querying the intermediate `ClinicalState` for missing or uncertain data.
  - **Synthesis agent** performs a shallow copy from `ClinicalState` to the final `PatientRecord` (no LLM calls needed).
- **Design Principles**:
  - Provider‑agnostic (no LLM vendor lock‑in).
  - Traceable, auditable, and confidence‑scored data.
  - Extensible schema that can evolve without breaking existing pipelines.

---

## What We Have Built So Far

| Component | Status | Details |
|-----------|--------|---------|
| **Schema Layer** | ✅ Completed | Core Pydantic models (`PatientRecord`, `PatientDatabase`, etc.) under `src/schemas/`.
| **ClinicalState** | ✅ Completed | Intermediate representation (`ClinicalState`, `Conflict`, `SectionStatus`, helpers) with planner query methods.
| **Evidence & Confidence** | ✅ Completed | Reusable base models in `src/schemas/base.py` (timezone‑aware timestamps). |
| **Export Logic** | ✅ Completed | `src/storage/json_writer.py` writes extracted data to `data/structured_json/`.
| **Extraction Stubs** | ✅ Implemented | `pdf_processor.py` (PDF → PNG) and `vlm_extractor.py` (image → markdown via Gemini API). |
| **Pipeline Script** | ✅ Updated | `run_pipeline.py` now uses `python-dotenv` for API key, dynamic data dirs, and a 10‑second pacing delay. |
| **Documentation** | ✅ Added | Detailed `clinical_state_design.md` explains the intermediate representation. |
| **Version Control** | ✅ Committed | Latest changes committed (SHA `56152e2`). |

---

## Next Steps

1. **Implement agents** – extraction, validation, consensus, planner, and synthesis modules that operate on `ClinicalState`.
2. **Add unit tests** for schema validation and state helpers.
3. **Set up CI** to enforce schema version compatibility.
4. **Integrate with a real LLM** (Gemini, Claude, etc.) while keeping the schema layer provider‑agnostic.
5. **Finalize orchestration** (e.g., using a simple task runner or workflow engine).

---

## Getting Started

```bash
# Install dependencies
pip install -r requirements.txt   # includes pydantic, pdf2image, pillow, python-dotenv, google-genai

# Set your Gemini (or other) API key
cp .env.example .env
# edit .env and add GEMINI_API_KEY=your_key

# Run the pipeline (example for a single PDF)
python run_pipeline.py
```

---

*Feel free to explore the `src/` hierarchy – the schema layer lives under `src/schemas/`, and the interim state lives in `src/schemas/state.py`. All future agents will read/write to `ClinicalState`.*
