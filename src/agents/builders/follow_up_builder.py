# src/agents/builders/follow_up_builder.py
"""
FollowUpBuilder — extracts follow-up care instructions.

Singleton builder. Returns Optional[FollowUp] in result.section_data.
Note: FollowUp itself contains nested lists (appointments,
monitoring_requirements, return_precautions) which require
sub-model coercion.

Usage:
    builder = FollowUpBuilder(extraction_json=..., api_key="...")
    result = builder.build()
    state.follow_up = result.section_data
"""

from datetime import date
from typing import List, Optional

from src.schemas.clinical import (
    FollowUp,
    Appointment,
    MonitoringRequirement,
    ReturnPrecaution,
)

from src.agents.builders.base_builder import BaseSectionBuilder
from src.agents.prompts.follow_up_prompt import (
    SYSTEM_INSTRUCTION,
    build_user_prompt,
)


class FollowUpBuilder(BaseSectionBuilder):
    """Extracts follow-up appointments, monitoring, and return precautions."""

    SECTION_NAME = "follow_up"
    BUILDER_NAME = "FollowUpBuilder"
    REQUIRED_FIELDS = ["appointments"]

    def _get_system_instruction(self) -> str:
        return SYSTEM_INSTRUCTION

    def _build_user_prompt(self) -> str:
        return build_user_prompt(self.extraction_json)

    def _parse_section_model(self, llm_response: dict) -> Optional[FollowUp]:
        """
        Parse 'follow_up' from the LLM response.
        Coerces nested lists of appointments, monitoring requirements,
        and return precautions into their respective Pydantic models.
        """
        raw = llm_response.get("follow_up")
        if not raw or not isinstance(raw, dict):
            return None

        self.clean_null_strings(raw)

        # Coerce appointments
        raw["appointments"] = self._parse_appointments(
            raw.get("appointments", [])
        )

        # Coerce monitoring requirements
        raw["monitoring_requirements"] = self._parse_monitoring(
            raw.get("monitoring_requirements", [])
        )

        # Coerce return precautions
        raw["return_precautions"] = self._parse_precautions(
            raw.get("return_precautions", [])
        )

        try:
            return FollowUp(**raw)
        except Exception:
            return None

    # ── Helpers ───────────────────────────────────────────────

    @staticmethod
    def _parse_appointments(raw_list) -> List[Appointment]:
        """Parse raw appointment dicts into Appointment models."""
        if not isinstance(raw_list, list):
            return []

        appointments = []
        for raw in raw_list:
            if not isinstance(raw, dict):
                continue

            # Coerce follow_up_date
            fd = raw.get("follow_up_date")
            if isinstance(fd, str):
                try:
                    raw["follow_up_date"] = date.fromisoformat(fd)
                except (ValueError, TypeError):
                    raw["follow_up_date"] = None

            try:
                appointments.append(Appointment(**raw))
            except Exception:
                continue

        return appointments

    @staticmethod
    def _parse_monitoring(raw_list) -> List[MonitoringRequirement]:
        """Parse raw monitoring dicts into MonitoringRequirement models."""
        if not isinstance(raw_list, list):
            return []

        items = []
        for raw in raw_list:
            if not isinstance(raw, dict):
                continue
            param = raw.get("parameter")
            freq = raw.get("frequency")
            if param and freq:
                items.append(
                    MonitoringRequirement(parameter=param, frequency=freq)
                )

        return items

    @staticmethod
    def _parse_precautions(raw_list) -> List[ReturnPrecaution]:
        """Parse raw precaution dicts into ReturnPrecaution models."""
        if not isinstance(raw_list, list):
            return []

        items = []
        for raw in raw_list:
            if not isinstance(raw, dict):
                continue
            sign = raw.get("warning_sign")
            action = raw.get("recommended_action")
            if sign and action:
                items.append(
                    ReturnPrecaution(warning_sign=sign, recommended_action=action)
                )

        return items
