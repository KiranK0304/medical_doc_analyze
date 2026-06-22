# src/agents/orchestrator.py
"""
Orchestrator — runs all 9 section builders and assembles a ClinicalState.

This is the "glue" that connects extraction JSON to a fully hydrated
ClinicalState. It:
    1. Instantiates every builder from BUILDER_REGISTRY
    2. Runs each builder sequentially (fault-isolated)
    3. Merges each BuilderResult into the shared ClinicalState
    4. Returns the completed ClinicalState

Usage:
    from src.agents.orchestrator import build_clinical_state

    state = build_clinical_state(
        extraction_json=loaded_json,
        api_key="...",
        source_document="clinical_chart.pdf",
        case_id="case_001",
    )
"""

import time
from typing import List, Tuple, Type

from src.schemas.state import ClinicalState

from src.agents.builders.base_builder import BaseSectionBuilder, BuilderResult

# ── All builders ─────────────────────────────────────────────
from src.agents.builders.patient_details_builder import PatientDetailsBuilder
from src.agents.builders.admission_details_builder import AdmissionDetailsBuilder
from src.agents.builders.diagnoses_builder import DiagnosesBuilder
from src.agents.builders.procedures_builder import ProceduresBuilder
from src.agents.builders.investigations_builder import InvestigationsBuilder
from src.agents.builders.medications_builder import MedicationsBuilder
from src.agents.builders.hospital_course_builder import HospitalCourseBuilder
from src.agents.builders.discharge_status_builder import DischargeStatusBuilder
from src.agents.builders.follow_up_builder import FollowUpBuilder
# from .. agents.builders.follow_up_builder import FollowUpBuilder


# ── Builder registry ────────────────────────────────────────
# Each entry maps:  (section_name, builder_class, is_list_section)
# Adding or removing a builder is a one-line change here.
BUILDER_REGISTRY: List[Tuple[str, Type[BaseSectionBuilder], bool]] = [
    ("patient_details",   PatientDetailsBuilder,   False),
    ("admission_details", AdmissionDetailsBuilder, False),
    ("diagnoses",         DiagnosesBuilder,         True),
    ("procedures",        ProceduresBuilder,        True),
    ("investigations",    InvestigationsBuilder,    True),
    ("medications",       MedicationsBuilder,       True),
    ("hospital_course",   HospitalCourseBuilder,    False),
    ("discharge_status",  DischargeStatusBuilder,   False),
    ("follow_up",         FollowUpBuilder,          False),
]


def build_clinical_state(
    extraction_json: dict,
    api_key: str,
    source_document: str = "unknown_document",
    case_id: str = "unknown_case",
) -> ClinicalState:
    """
    Run all section builders and assemble a ClinicalState.

    Each builder is fault-isolated: if one fails, the rest still run.
    Failures are recorded as flags and the section is marked EMPTY.

    Args:
        extraction_json: The extraction JSON from the VLM pipeline.
        api_key: API key for LLM calls.
        source_document: Name of the source PDF.
        case_id: Unique case identifier.

    Returns:
        A fully hydrated ClinicalState with all sections populated.
    """
    state = ClinicalState(case_id=case_id)

    total_start = time.time()

    for section_name, builder_class, is_list in BUILDER_REGISTRY:
        print(f"  🔧 Running {builder_class.BUILDER_NAME}...")
        section_start = time.time()

        try:
            builder = builder_class(
                extraction_json=extraction_json,
                api_key=api_key,
                source_document=source_document,
                case_id=case_id,
            )
            result: BuilderResult = builder.build()
        except Exception as e:
            # Catastrophic builder failure (import error, init crash, etc.)
            print(f"  ❌ {builder_class.BUILDER_NAME} crashed: {e}")
            continue

        # ── Merge result into ClinicalState ──────────────────
        _merge_result(state, section_name, result, is_list)

        elapsed = time.time() - section_start
        status = result.section_status.status.value
        print(f"  ✅ {builder_class.BUILDER_NAME} → {status} ({elapsed:.1f}s)")

    total_elapsed = time.time() - total_start
    print(f"\n📊 Orchestrator complete in {total_elapsed:.1f}s")
    _print_summary(state)

    return state


def _merge_result(
    state: ClinicalState,
    section_name: str,
    result: BuilderResult,
    is_list: bool,
) -> None:
    """
    Merge a single BuilderResult into the ClinicalState.

    - Singleton sections: assign section_data directly
    - List sections: assign section_data or empty list
    - Flags, conflicts, completeness: always merge
    """
    # Section data
    if is_list:
        setattr(state, section_name, result.section_data or [])
    else:
        setattr(state, section_name, result.section_data)

    # Flags
    state.flags.extend(result.flags)

    # Conflicts
    state.conflicts.extend(result.conflicts)

    # Completeness tracker
    state.completeness_tracker[section_name] = result.section_status


def _print_summary(state: ClinicalState) -> None:
    """Print a brief summary of the orchestration results."""
    missing = state.get_missing_sections()
    partial = state.get_partial_sections()
    conflicts = state.get_unresolved_conflicts()

    print(f"  Sections:   {len(BUILDER_REGISTRY)} total")
    print(f"  Missing:    {len(missing)} — {missing}")
    print(f"  Partial:    {len(partial)} — {partial}")
    print(f"  Flags:      {len(state.flags)}")
    print(f"  Conflicts:  {len(conflicts)} unresolved")
