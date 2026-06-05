from pydantic import BaseModel, Field
from typing import Dict, List, Optional
from datetime import datetime
from .base import Flag, Evidence, Confidence
from .clinical import (
    PatientDetails, AdmissionDetails, Diagnosis, Procedure,
    Investigation, Medication, HospitalCourse, DischargeStatus, FollowUp
)

class ProcessingMetadata(BaseModel):
    processing_timestamp: datetime = Field(default_factory=datetime.utcnow)
    schema_version: str = "1.0.0"
    source_document_count: int
    source_page_count: int
    processing_duration_seconds: float
    system_version: str

class PatientRecord(BaseModel):
    # 1. Patient Details
    patient_details: Optional[PatientDetails] = None
    
    # 2. Admission Details
    admission_details: Optional[AdmissionDetails] = None
    
    # 3. Diagnoses
    diagnoses: List[Diagnosis] = Field(default_factory=list)
    
    # 4. Procedures
    procedures: List[Procedure] = Field(default_factory=list)
    
    # 5. Investigations
    investigations: List[Investigation] = Field(default_factory=list)
    
    # 6. Medications
    medications: List[Medication] = Field(default_factory=list)
    
    # 7. Hospital Course
    hospital_course: Optional[HospitalCourse] = None
    
    # 8. Discharge Status
    discharge_status: Optional[DischargeStatus] = None
    
    # 9. Follow-up
    follow_up: Optional[FollowUp] = None
    
    # 10. Flags / Concerns
    flags: List[Flag] = Field(default_factory=list)
    
    # 11. Evidence Map
    evidence_map: Dict[str, List[Evidence]] = Field(default_factory=dict, description="Map of element IDs to extracted evidence")
    
    # 12. Confidence Metadata
    confidence_metadata: Dict[str, Confidence] = Field(default_factory=dict, description="Map of element IDs to confidence scores")
    
    # 13. Processing Metadata
    processing_metadata: Optional[ProcessingMetadata] = None

class PatientDatabase(BaseModel):
    """Top-Level Structure mapping patient_identifier to PatientRecord"""
    records: Dict[str, PatientRecord] = Field(default_factory=dict)
