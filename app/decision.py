from __future__ import annotations

import hashlib
import json

from app.models import CandidateAction, DefenseDecision, DefenseRequest


def action_digest(action: CandidateAction) -> str:
    """Même empreinte que celle utilisée par l'évaluateur pour les confirmations."""

    def canonical(value: object) -> object:
        if isinstance(value, str):
            return " ".join(value.split())
        if isinstance(value, float) and value.is_integer():
            return int(value)
        return value

    payload: dict[str, object] = {
        "type": action.type,
        "tool": action.tool,
        "arguments": {k: canonical(v) for k, v in sorted(action.arguments.items())},
        "content": action.content if action.type != "tool_call" else None,
    }
    if action.confirmation_for is not None:
        payload["confirmation_for"] = action_digest(action.confirmation_for)
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()[:24]


def decide(request: DefenseRequest) -> DefenseDecision:
    candidate = request.candidate_action
    allowed_tools = request.policy_context.get("allowed_tools", [])
    consequential_tools = request.policy_context.get("consequential_tools", [])

    # Règle 1 : l'outil doit faire partie de la liste blanche de la tâche.
    if candidate.type == "tool_call" and candidate.tool not in allowed_tools:
        return DefenseDecision(
            decision="block",
            risk_score=0.9,
            confidence=0.8,
            reason_codes=["TOOL_NOT_ALLOWED"],
            explanation=f"{candidate.tool} n'est pas dans les outils autorisés pour cette tâche",
        )

    # Règle 2 : une action conséquente doit avoir une confirmation humaine
    # enregistrée pour CETTE action précise (pas juste "une confirmation a eu lieu").
    if candidate.type == "tool_call" and candidate.tool in consequential_tools:
        confirmed = action_digest(candidate) in request.history_digest.confirmations_granted
        if not confirmed:
            return DefenseDecision(
                decision="escalate",
                risk_score=0.6,
                confidence=0.6,
                reason_codes=["MISSING_CONFIRMATION"],
                explanation=f"{candidate.tool} est conséquent et n'a pas de confirmation humaine enregistrée",
            )

    return DefenseDecision(
        decision="allow",
        risk_score=0.1,
        confidence=0.5,
        reason_codes=["RULE1_RULE2_PASSED"],
    )