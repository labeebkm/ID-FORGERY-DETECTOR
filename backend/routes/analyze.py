import time

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from backend.models import (
    ErrorResponse,
    ForensicAnalysisBreakdown,
    FraudReport,
    GeminiAnalysis,
    ValidationResult,
)
from backend.services import (
    FraudSignals,
    combine_signals,
    run_blur_analysis,
    run_edge_detection,
    run_ela_analysis,
    run_gemini_analysis,
    run_metadata_analysis,
    run_noise_analysis,
)
from backend.utils import load_image_pil, validate_image_bytes

router = APIRouter()


@router.post(
    "/analyze-id",
    response_model=FraudReport,
    responses={
        status.HTTP_400_BAD_REQUEST: {
            "model": ErrorResponse,
            "description": "Validation or decoding error.",
        }
    },
    summary="Analyze an ID document image for forgery indicators",
)
async def analyze_id(image: UploadFile = File(...)) -> FraudReport:
    """
    Full forensic pipeline: 5 classical CV checks + Gemini Vision LLM.
    Scores are fused 50/50 into a final risk score.
    """
    try:
        raw_bytes = await image.read()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ErrorResponse(message="Failed to read file.", details=str(exc)).dict(),
        )

    mime_type = image.content_type
    validation = validate_image_bytes(raw_bytes, mime_type)

    if not validation.is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ErrorResponse(
                message="Image validation failed.",
                details="; ".join(validation.reasons),
            ).dict(),
        )

    pil_image = load_image_pil(raw_bytes)
    start = time.perf_counter()

    # Classical CV pipeline
    ela_result      = run_ela_analysis(pil_image)
    noise_result    = run_noise_analysis(pil_image)
    edge_result     = run_edge_detection(pil_image)
    blur_result     = run_blur_analysis(pil_image)
    metadata_result = run_metadata_analysis(pil_image)

    # Gemini Vision LLM
    gemini_result = run_gemini_analysis(pil_image)

    # Fuse classical signals
    fraud_signals = FraudSignals(
        ela_score=ela_result.score,
        noise_score=noise_result.score,
        noise_anomaly=noise_result.anomaly,
        edge_score=edge_result.score,
        edge_artifacts=edge_result.has_artifacts,
        blur_score=blur_result.score,
        blur_inconsistency=blur_result.has_inconsistency,
        metadata_flag=metadata_result.has_flag,
        metadata_flags=metadata_result.flags,
    )
    cv_result = combine_signals(fraud_signals)

    # Blend CV + Gemini 50/50
    if gemini_result.available:
        gemini_100 = int(gemini_result.score * 100)
        final_score = int(cv_result.risk_score * 0.5 + gemini_100 * 0.5)
        if gemini_result.confidence >= 70:
            verdict_map = {
                "LIKELY_FORGED": "Suspicious",
                "SUSPICIOUS":    "Medium Risk",
                "GENUINE":       "Likely Genuine",
            }
            risk_level = verdict_map.get(gemini_result.verdict, cv_result.risk_level)
        else:
            risk_level = cv_result.risk_level
        explanation = (
            f"[AI Vision] {gemini_result.reasoning} "
            f"[Forensic CV] {cv_result.explanation}"
        )
    else:
        final_score = cv_result.risk_score
        risk_level  = cv_result.risk_level
        explanation = cv_result.explanation

    final_score = max(0, min(100, final_score))
    processing_time_ms = int((time.perf_counter() - start) * 1000)

    return FraudReport(
        risk_score=final_score,
        risk_level=risk_level,
        analysis=ForensicAnalysisBreakdown(
            ela_score=round(ela_result.score, 4),
            noise_anomaly=noise_result.anomaly,
            edge_artifacts=edge_result.has_artifacts,
            blur_inconsistency=blur_result.has_inconsistency,
            metadata_flag=metadata_result.has_flag,
        ),
        gemini=GeminiAnalysis(
            verdict=gemini_result.verdict,
            suspicion_score=round(gemini_result.score, 3),
            confidence=gemini_result.confidence,
            reasoning=gemini_result.reasoning,
            available=gemini_result.available,
        ),
        explanation=explanation,
        processing_time_ms=processing_time_ms,
        validation=validation,
        ela_visual=ela_result.heatmap_b64,
        edge_visual=edge_result.edge_map_b64,
        tamper_overlay_visual=ela_result.heatmap_b64,
    )
