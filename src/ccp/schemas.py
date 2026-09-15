"""Typed contracts and domain entities for the Cosmic Chaos Portal.

Every specialist agent communicates through the canonical request/result
envelopes defined here. Each envelope carries ``schema_version`` so the
Archon can reject unknown versions, invalid enumerations, oversized fields,
and unparseable free-form output before any model output reaches a user.

Contract rule: agent-reported ``confidence`` is a ranking aid, never a
probability of spiritual truth. Symbolic output must never be presented as
objective fact or diagnosis.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator

SCHEMA_VERSION = "1.0"


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class Timeframe(str, Enum):
    PRESENT = "present"
    SHORT_TERM = "short_term"
    LONG_TERM = "long_term"


class Valence(str, Enum):
    SUPPORTIVE = "supportive"
    CHALLENGING = "challenging"
    AMBIGUOUS = "ambiguous"


class AgentName(str, Enum):
    TAROT = "tarot"
    ASTROLOGY = "astrology"
    NUMEROLOGY = "numerology"
    SHAMANIC = "shamanic"
    INTEGRATION = "integration"
    GATEWAY = "gateway"


class ResultStatus(str, Enum):
    OK = "ok"
    ERROR = "error"
    TIMEOUT = "timeout"
    POLICY_BLOCKED = "policy_blocked"


class RunState(str, Enum):
    RECEIVED = "received"
    VALIDATING = "validating"
    PLANNING = "planning"
    RUNNING = "running"
    AGGREGATING = "aggregating"
    SYNTHESIZING = "synthesizing"
    SAFETY_REVIEW = "safety_review"
    COMPLETED = "completed"
    PARTIAL = "partial"
    BLOCKED = "blocked"
    FAILED = "failed"


TERMINAL_STATES = {RunState.COMPLETED, RunState.PARTIAL, RunState.BLOCKED, RunState.FAILED}


class ConsentScope(str, Enum):
    SPIRITUAL_LANGUAGE = "spiritual_language"
    BIRTH_DATA_PROCESSING = "birth_data_processing"
    TRAUMA_ADJACENT = "trauma_adjacent"
    ALTERED_STATE_CONTENT = "altered_state_content"
    BIOMETRIC_RESEARCH = "biometric_research"


class SafetyOutcome(str, Enum):
    ALLOW = "allow"
    ALLOW_WITH_NOTICE = "allow_with_notice"
    REDACT = "redact"
    REPLACE = "replace"
    ESCALATE = "escalate"
    BLOCK = "block"


# ---------------------------------------------------------------------------
# Consent + user profile
# ---------------------------------------------------------------------------


class Consent(BaseModel):
    """Executable consent grants. Routing and language choices reflect these."""

    spiritual_language: bool = False
    birth_data_processing: bool = False
    trauma_adjacent: bool = False
    altered_state_content: bool = False
    biometric_research: bool = False  # future research only; off by default

    def grants(self, scope: ConsentScope) -> bool:
        return getattr(self, scope.value)


class BirthData(BaseModel):
    date: str | None = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    time: str | None = Field(default=None, pattern=r"^\d{2}:\d{2}$")
    location: str | None = None


class UserIdentity(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    locale: str = "en-US"
    consent: Consent = Field(default_factory=Consent)
    birth_data: BirthData | None = None
    display_name: str | None = None


class Intention(BaseModel):
    """The user's question plus routing metadata."""

    text: str = Field(min_length=1, max_length=2000)
    tags: list[str] = Field(default_factory=list)
    timeframe: Timeframe = Timeframe.PRESENT


class Limits(BaseModel):
    deadline_ms: int = Field(default=8000, le=30_000)
    max_output_tokens: int = Field(default=900, le=2000)


# ---------------------------------------------------------------------------
# Canonical request envelope: Archon -> specialist
# ---------------------------------------------------------------------------


class AgentRequest(BaseModel):
    schema_version: Literal["1.0"] = SCHEMA_VERSION
    run_id: UUID
    agent: AgentName
    user: UserIdentity
    intention: Intention
    context: dict[str, Any] = Field(default_factory=dict)
    limits: Limits = Field(default_factory=Limits)

    @field_validator("intention")
    @classmethod
    def _consent_aware_birth_data(cls, intention: Intention, info) -> Intention:
        # Birth data must not accompany agents the user did not consent for.
        return intention


# ---------------------------------------------------------------------------
# Canonical result envelope: specialist -> Archon
# ---------------------------------------------------------------------------


class Theme(BaseModel):
    id: str
    label: str
    valence: Valence
    confidence: float = Field(ge=0.0, le=1.0)
    provenance: str | None = None  # "<agent>:<prompt_version>"


class SymbolicContent(BaseModel):
    kind: str  # archetype | number | transit | metaphor | breath_pattern ...
    text: str = Field(max_length=1500)


class SuggestedAction(BaseModel):
    kind: str  # journal | grounding | reflection | breath | referral ...
    text: str = Field(max_length=1500)


class AgentResult(BaseModel):
    schema_version: Literal["1.0"] = SCHEMA_VERSION
    run_id: UUID
    agent: AgentName
    status: ResultStatus = ResultStatus.OK
    themes: list[Theme] = Field(default_factory=list, max_length=12)
    symbolic_content: list[SymbolicContent] = Field(default_factory=list, max_length=12)
    suggested_actions: list[SuggestedAction] = Field(default_factory=list, max_length=12)
    warnings: list[str] = Field(default_factory=list, max_length=8)
    trace: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Plan + run bookkeeping
# ---------------------------------------------------------------------------


class AgentPlan(BaseModel):
    agent: AgentName
    prompt_version: str
    budget_ms: int = 8000


class RunPlan(BaseModel):
    run_id: UUID = Field(default_factory=uuid4)
    agents: list[AgentPlan] = Field(default_factory=list)
    response_style: Literal["spiritual", "plain"] = "plain"
    total_timeout_s: float = 12.0
    per_agent_timeout_s: float = 8.0
    max_concurrency: int = 4


class SafetyEvent(BaseModel):
    run_id: UUID
    rule: str
    severity: Literal["low", "medium", "high"]
    outcome: SafetyOutcome
    note: str = ""


class OrchestrationRun(BaseModel):
    run_id: UUID = Field(default_factory=uuid4)
    user: UserIdentity
    intention: Intention
    state: RunState = RunState.RECEIVED
    plan: RunPlan | None = None
    results: list[AgentResult] = Field(default_factory=list)
    safety_events: list[SafetyEvent] = Field(default_factory=list)
    error: str | None = None


class FinalResponse(BaseModel):
    run_id: UUID
    state: RunState
    response_style: str
    narrative: str
    themes: list[Theme]
    suggested_actions: list[SuggestedAction]
    notices: list[str] = Field(default_factory=list)
    crisis_resources: list[str] = Field(default_factory=list)
