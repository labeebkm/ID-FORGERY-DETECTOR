from dataclasses import dataclass
from typing import List


@dataclass
class FraudSignals:
    ela_score: float
    noise_score: float
    noise_anomaly: bool
    edge_score: float
    edge_artifacts: bool
    blur_score: float
    blur_inconsistency: bool
    metadata_flag: bool
    metadata_flags: List[str]


@dataclass
class FraudScoreResult:
    risk_score: int   # 0–100
    risk_level: str
    explanation: str


def combine_signals(signals: FraudSignals) -> FraudScoreResult:
    """
    Fuse forensic signals into a transparent, auditable risk score.

    Weights are intentionally conservative to reduce false positives on
    genuine documents that happen to have unusual compression histories.
    """
    base = 0.0

    # ELA is the strongest signal — up to 40 points
    base += 40.0 * signals.ela_score

    # Noise, edge, blur — up to 15 points each
    base += 15.0 * signals.noise_score
    base += 15.0 * signals.edge_score
    base += 15.0 * signals.blur_score

    # Binary anomaly boosts
    if signals.noise_anomaly:
        base += 5.0
    if signals.edge_artifacts:
        base += 5.0
    if signals.blur_inconsistency:
        base += 5.0
    if signals.metadata_flag:
        base += 5.0

    risk_score = int(max(0, min(100, round(base))))

    if risk_score < 30:
        level = "Likely Genuine"
    elif risk_score < 60:
        level = "Medium Risk"
    else:
        level = "Suspicious"

    reasons: List[str] = []

    if signals.ela_score > 0.6:
        reasons.append("Strong ELA compression inconsistencies detected — regions may have been edited.")
    elif signals.ela_score > 0.3:
        reasons.append("Moderate ELA anomalies suggest possible prior re-saves or local edits.")

    if signals.noise_anomaly:
        reasons.append("Noise patterns vary abnormally across regions, suggesting composite origin.")
    if signals.edge_artifacts:
        reasons.append("Unnatural edge structures indicate possible splicing or compositing.")
    if signals.blur_inconsistency:
        reasons.append("Sharpness is inconsistent across the document — may indicate pasted regions.")
    if signals.metadata_flag:
        reasons.extend(signals.metadata_flags or ["EXIF metadata contains atypical or missing fields."])

    if not reasons:
        reasons.append(
            "No significant forgery cues detected. Risk score reflects mild statistical deviations only."
        )

    return FraudScoreResult(
        risk_score=risk_score,
        risk_level=level,
        explanation=" ".join(reasons),
    )
