from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date, datetime
from enum import Enum
from .base import ClinicalBase

class DiagnosisType(str, Enum):
    PRIMARY = "primary"
    SECONDARY = "secondary"
    COMORBIDITY = "comorbidity"
    DISCHARGE = "discharge"

class DiagnosisStatus(str, Enum):
    ACTIVE = "active"
    RESOLVED = "resolved"
    SUSPECTED = "suspected"
    HISTORICAL = "historical"
    UNKNOWN = "unknown"

class Diagnosis(ClinicalBase):
    diagnosis_name: str
    diagnosis_code: Optional[str] = None
    diagnosis_type: DiagnosisType
    diagnosis_status: DiagnosisStatus
    diagnosis_date: Optional[date] = None
    notes: Optional[str] = None

class Procedure(ClinicalBase):
    procedure_name: str
    procedure_code: Optional[str] = None
    procedure_date: Optional[date] = None
    indication: Optional[str] = None
    outcome: Optional[str] = None
    performing_department: Optional[str] = None
    notes: Optional[str] = None

class InvestigationCategory(str, Enum):
    LABORATORY = "laboratory"
    RADIOLOGY = "radiology"
    PATHOLOGY = "pathology"
    MICROBIOLOGY = "microbiology"
    CARDIOLOGY = "cardiology"
    OTHER = "other"

class Investigation(ClinicalBase):
    investigation_name: str
    category: InvestigationCategory
    result: Optional[str] = None
    normal_range: Optional[str] = None
    interpretation: Optional[str] = None
    investigation_date: Optional[date] = None

class MedicationStatus(str, Enum):
    STARTED = "started"
    CONTINUED = "continued"
    MODIFIED = "modified"
    STOPPED = "stopped"
    COMPLETED = "completed"
    UNKNOWN = "unknown"

class Medication(ClinicalBase):
    medication_name: str
    generic_name: Optional[str] = None
    dose: Optional[str] = None
    dosage_unit: Optional[str] = None
    frequency: Optional[str] = None
    route: Optional[str] = None
    indication: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    status: MedicationStatus

class PatientDetails(ClinicalBase):
    patient_id: str
    medical_record_number: Optional[str] = None
    patient_name: Optional[str] = None
    age: Optional[int] = None
    age_unit: Optional[str] = None
    gender: Optional[str] = None
    date_of_birth: Optional[date] = None
    address: Optional[str] = None
    contact_information: Optional[str] = None

class AdmissionDetails(ClinicalBase):
    admission_id: str
    admission_date: Optional[date] = None
    discharge_date: Optional[date] = None
    length_of_stay: Optional[int] = None
    hospital_name: Optional[str] = None
    department: Optional[str] = None
    attending_physician: Optional[str] = None
    referring_physician: Optional[str] = None
    admission_reason: Optional[str] = None
    chief_complaints: List[str] = Field(default_factory=list)

class Event(BaseModel):
    timestamp: datetime
    description: str

class HospitalCourse(ClinicalBase):
    admission_summary: Optional[str] = None
    key_clinical_events: List[Event] = Field(default_factory=list)
    complications: Optional[str] = None
    treatment_response: Optional[str] = None
    discharge_summary: Optional[str] = None

class DischargeStatus(ClinicalBase):
    discharge_condition: Optional[str] = None
    functional_status: Optional[str] = None
    cognitive_status: Optional[str] = None
    mobility_status: Optional[str] = None
    diet_instructions: Optional[str] = None
    activity_instructions: Optional[str] = None
    discharge_destination: Optional[str] = None

class Appointment(ClinicalBase):
    specialty: Optional[str] = None
    provider: Optional[str] = None
    follow_up_date: Optional[date] = None
    purpose: Optional[str] = None

class MonitoringRequirement(BaseModel):
    parameter: str
    frequency: str

class ReturnPrecaution(BaseModel):
    warning_sign: str
    recommended_action: str

class FollowUp(ClinicalBase):
    appointments: List[Appointment] = Field(default_factory=list)
    medication_instructions: Optional[str] = None
    monitoring_requirements: List[MonitoringRequirement] = Field(default_factory=list)
    return_precautions: List[ReturnPrecaution] = Field(default_factory=list)
