from __future__ import annotations

from app.models import DefenseDecision, DefenseRequest


def decide(request: DefenseRequest) -> DefenseDecision:
    return DefenseDecision(
        decision="allow",
        risk_score=0.0,
        confidence=0.5,
        reason_codes=["PLACEHOLDER_ALLOW_ALL"],
    )