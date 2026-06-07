from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, timezone
from enum import Enum

class Severity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class Evidence(BaseModel):
    source_document: str
    page_number: Optional[int] = None
    section_name: Optional[str] = None
    extracted_text: str
    extraction_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class Confidence(BaseModel):
    confidence_score: float = Field(ge=0.0, le=1.0)
    confidence_reason: Optional[str] = None

class AuditInformation(BaseModel):
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: str
    last_modified_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_modified_by: str

class ReviewItem(BaseModel):
    issue: str
    reason: str
    severity: Severity

class Flag(BaseModel):
    flag_type: str  # e.g., "Clinical Flag", "Data Quality Flag"
    name: str       # e.g., "critical laboratory value", "missing discharge date"
    description: Optional[str] = None
    review_required: Optional[ReviewItem] = None

class ClinicalBase(BaseModel):
    """
    Base model for clinical entities ensuring they support 
    evidence, confidence, and auditability.
    """
    evidence: List[Evidence] = Field(default_factory=list)
    confidence: Optional[Confidence] = None
    audit_info: Optional[AuditInformation] = None
