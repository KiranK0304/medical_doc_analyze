# docs/plan.md

# Project Planning Overview

## What we have built so far

1. **Canonical output schema** – `src/schemas/record.py` defines the final `PatientRecord` and `PatientDatabase` models that will be the JSON output of the system.
2. **Intermediate reasoning schema** – `src/schemas/state.py` introduces `ClinicalState`, a patient‑centric knowledge representation that mirrors the output schema but also includes:
   - `conflicts`: a list of `Conflict` objects for contradictory data.
   - `completeness_tracker`: a per‑section `SectionStatus` map that planners can query to know what is missing or incomplete.
3. **PatientDetailsBuilder** – located at `src/agents/builders/patient_details_builder.py`. It:
   - Takes the extracted markdown JSON from the VLM.
   - Sends a focused prompt to the LLM.
   - Parses the response into a `PatientDetails` model, associated `Flag`s, `Conflict`s and a `SectionStatus`.
   - Returns a lightweight `BuilderResult` dataclass that the caller can merge into `ClinicalState`.

## What’s next?

- **Glue / orchestration layer** – we still need a small piece of code that:
  1. Loads the extraction JSON.
  2. Instantiates (or retrieves) a `ClinicalState` for the current case.
  3. Calls `PatientDetailsBuilder.build()`.
  4. Updates `ClinicalState.patient_details`, appends `flags` and `conflicts`, and writes the updated `completeness_tracker` entry.
- This glue will be added **after** we finish implementing the remaining builders (diagnosis, medication, investigations, etc.) so that the orchestration can simply iterate over all builder results.

---

### Why `BuilderResult` is a `dataclass` and not a Pydantic model?

`BuilderResult` is **only a transient container** used inside a single builder call. It:
- Holds already‑validated Pydantic objects (`PatientDetails`, `Flag`, `Conflict`, `SectionStatus`).
- Does not need runtime validation, JSON (de)serialization, or the extra metadata that Pydantic provides.
- Using a plain `dataclass` keeps it lightweight, fast, and free of the import‑time overhead that Pydantic models bring.
- If in the future we need to persist `BuilderResult` or expose it via an API, we can always convert it to a Pydantic model – but for now a `dataclass` is the simplest and most appropriate choice.

---

*All of the above will be reflected in the repository’s history through a few granular commits.*
