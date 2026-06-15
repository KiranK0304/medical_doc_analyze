# src/agents/builders/hospital_course_builder.py
"""
HospitalCourseBuilder — extracts hospital course narrative.

Singleton builder. Returns Optional[HospitalCourse] in result.section_data.

Usage:
    builder = HospitalCourseBuilder(extraction_json=..., api_key="...")
    result = builder.build()
    state.hospital_course = result.section_data
"""

from datetime import datetime
from typing import Optional

from src.schemas.clinical import HospitalCourse, Event

from src.agents.builders.base_builder import BaseSectionBuilder
from src.agents.prompts.hospital_course_prompt import (
    SYSTEM_INSTRUCTION,
    build_user_prompt,
)


class HospitalCourseBuilder(BaseSectionBuilder):
    """Extracts the hospital course narrative and key clinical events."""

    SECTION_NAME = "hospital_course"
    BUILDER_NAME = "HospitalCourseBuilder"
    REQUIRED_FIELDS = ["admission_summary"]

    def _get_system_instruction(self) -> str:
        return SYSTEM_INSTRUCTION

    def _build_user_prompt(self) -> str:
        return build_user_prompt(self.extraction_json)

    def _parse_section_model(self, llm_response: dict) -> Optional[HospitalCourse]:
        """
        Parse 'hospital_course' from the LLM response.
        Coerces key_clinical_events timestamps into datetime objects.
        """
        raw = llm_response.get("hospital_course")
        if not raw or not isinstance(raw, dict):
            return None

        self.clean_null_strings(raw)

        # Coerce key_clinical_events into Event objects
        raw_events = raw.get("key_clinical_events", [])
        events = []
        if isinstance(raw_events, list):
            for event_raw in raw_events:
                if not isinstance(event_raw, dict):
                    continue
                ts = self._coerce_datetime(event_raw.get("timestamp"))
                desc = event_raw.get("description", "")
                if ts and desc:
                    events.append(Event(timestamp=ts, description=desc))
        raw["key_clinical_events"] = events

        try:
            return HospitalCourse(**raw)
        except Exception:
            return None

    # ── Helpers ───────────────────────────────────────────────

    @staticmethod
    def _coerce_datetime(value) -> Optional[datetime]:
        """
        Parse an ISO 8601 datetime string, handling both full timestamps
        and date-only strings.
        """
        if not isinstance(value, str):
            return None
        for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M", "%Y-%m-%d"):
            try:
                return datetime.strptime(value, fmt)
            except ValueError:
                continue
        return None
