from pydantic import BaseModel, Field
from typing import Dict, List, Optional
from datetime import datetime, timezone
from .base import Flag, Evidence, Confidence
from .clinical import (
    PatientDetails, AdmissionDetails, Diagnosis, Procedure,
    Investigation, Medication, HospitalCourse, DischargeStatus, FollowUp
)

class ProcessingMetadata(BaseModel):
    processing_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    schema_version: str = "1.0.0"
    source_document_count: int
    source_page_count: int
    processing_duration_seconds: float
    system_version: str

class PatientRecord(BaseModel):
    patient_details: Optional[PatientDetails] = None

    admission_details: Optional[AdmissionDetails] = None
    
    diagnoses: List[Diagnosis] = Field(default_factory=list)
    
    procedures: List[Procedure] = Field(default_factory=list)
    
    investigations: List[Investigation] = Field(default_factory=list)
    
    medications: List[Medication] = Field(default_factory=list)
    
    hospital_course: Optional[HospitalCourse] = None
    
    discharge_status: Optional[DischargeStatus] = None
    
    follow_up: Optional[FollowUp] = None
    
    flags: List[Flag] = Field(default_factory=list)
    
    evidence_map: Dict[str, List[Evidence]] = Field(default_factory=dict, description="Map of element IDs to extracted evidence")
    
    confidence_metadata: Dict[str, Confidence] = Field(default_factory=dict, description="Map of element IDs to confidence scores")
    
    processing_metadata: Optional[ProcessingMetadata] = None

class PatientDatabase(BaseModel):
    """Top-Level Structure mapping patient_identifier to PatientRecord"""
    records: Dict[str, PatientRecord] = Field(default_factory=dict)
