"""Response contract for the emergency backend.

This mirrors the agent's output exactly. The field names are shared across the
whole project (agent, backend, frontend) and must not change:

    emergency_type, severity, confidence, reason, actions

``extra="forbid"`` is deliberate: if the agent ever grows a field, validation
fails loudly here rather than silently leaking an undocumented field to the
frontend.
"""

from pydantic import BaseModel, ConfigDict


class EmergencyAssessment(BaseModel):
    """The five canonical fields, and nothing else."""

    model_config = ConfigDict(extra="forbid")

    emergency_type: str
    severity: str
    confidence: float
    reason: str
    actions: list[str]


class ErrorResponse(BaseModel):
    """Every error the frontend can receive.

    ``frontend/src/services/api.js`` always calls ``response.json()`` and reads
    ``detail``, so errors must be JSON with a single human-readable sentence.
    """

    detail: str
