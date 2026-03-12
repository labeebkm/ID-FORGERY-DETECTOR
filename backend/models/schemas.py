from typing import List, Optional
from pydantic import BaseModel, Field


class ValidationResult(BaseModel):
    is_valid: bool
    reasons: List[str] = Field(default_factory=list)
    width: Optional[int] = None
    height: Optional[int] = None
    file_size_bytes: Optional[int] = None
    mime_type: Optional[str] = None


class ForensicAnalysisBreakdown(BaseModel):
    ela_score: float
    noise_anomaly: bool
    edge_artifacts: bool
    blur_inconsistency: bool
    metadata_flag: bool


class GeminiAnalysis(BaseModel):
    verdict: str
    suspicion_score: float
    confidence: int
    reasoning: str
    available: bool


class FraudReport(BaseModel):
    risk_score: int = Field(..., ge=0, le=100)
    risk_level: str
    analysis: ForensicAnalysisBreakdown
    gemini: Optional[GeminiAnalysis] = None
    warnings: List[str] = Field(default_factory=list)
    explanation: str
    processing_time_ms: int = Field(..., ge=0)
    validation: ValidationResult
    ela_visual: Optional[str] = None
    edge_visual: Optional[str] = None
    tamper_overlay_visual: Optional[str] = None


class ErrorResponse(BaseModel):
    message: str
    details: Optional[str] = None
