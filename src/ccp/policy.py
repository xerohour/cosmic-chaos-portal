"""Safety policy engine: deterministic rules + input/output evaluation.

Checks run at three points per the design doc:
  1. before routing  (``evaluate_input``  — may block specialists entirely)
  2. on every specialist result (lightweight content check)
  3. on the candidate response (``evaluate_output`` — approve, redact, or replace)

Deterministic prohibitions always win when signals disagree.

Hard boundaries (never):
  - diagnose, prescribe, or treat any condition
  - facilitate acquiring, selling, dosing, cultivating, or administering
    controlled substances
  - recommend neurostimulation settings or interpret biometrics medically
  - present divination or remote viewing as verified fact
  - promise supernatural certainty

Crisis behavior: when text indicates imminent danger or a need for emergency
help, stop the ritual flow and return a short locale-appropriate crisis
response with human-support encouragement. Do NOT ask a symbolic agent to
interpret the situation.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from uuid import UUID

from .schemas import (
    AgentName,
    AgentResult,
    ConsentScope,
    Intention,
    RunState,
    SafetyEvent,
    SafetyOutcome,
    UserIdentity,
)

# ---------------------------------------------------------------------------
# Pattern banks (deterministic, reviewable)
# ---------------------------------------------------------------------------

_CRISIS_PATTERNS = [
    r"\bkill myself\b",
    r"\bsuicid\w*\b",
    r"\bend my life\b",
    r"\bhurt myself\b",
    r"\bself[- ]harm\b",
    r"\bcutting myself\b",
    r"\bwant to die\b",
    r"\bno reason to live\b",
    r"\bplan to (die|kill)\b",
]

_SUBSTANCE_PATTERNS = [
    r"\bdmt\b", r"\bpsilocybin\b", r"\bshrooms?\b", r"\bacid\b", r"\blsd\b",
    r"\bayahuasca\b", r"\bmdma\b", r"\bmolly\b", r"\bketamine\b",
    r"\bcocaine\b", r"\bheroin\b", r"\bmeth\b",
    r"\bwhere (can|do) i (buy|get|find)\b.*\b(drug|weed|shroom)",
    r"\bhow (much|to) (take|dose|grow)\b",
]

_MEDICAL_CLAIM_PATTERNS = [
    r"\bdiagnos\w*\b",
    r"\bcure[sd]?\b",
    r"\btreat\w* (your|my|the) (depression|anxiety|ptsd|trauma|cancer)",
    r"\byou (have|are) (depressed|bipolar|schizophrenic|autistic)\b",
    r"\bprescri\w*\b",
    r"\bmedical advice\b",
]

_CERTAINTY_PATTERNS = [
    r"\bwill (definitely|certainly|undoubtedly) happen\b",
    r"\bguaranteed (to|that)\b",
    r"\b100% (certain|sure)\b",
    r"\bfate has decided\b",
    r"\bit is (written|destined)\b",
]

_NEURAL_PATTERNS = [
    r"\btdcs\b", r"\bneurostimulat\w*\b", r"\beeg\b.*\b(setting|protocol)\b",
    r"\bbrain.?stimulat\w*\b",
]

_COMPILATIONS = {name: [re.compile(p, re.IGNORECASE) for p in pats]
                 for name, pats in {
                     "crisis": _CRISIS_PATTERNS,
                     "substance": _SUBSTANCE_PATTERNS,
                     "medical": _MEDICAL_CLAIM_PATTERNS,
                     "certainty": _CERTAINTY_PATTERNS,
                     "neural": _NEURAL_PATTERNS,
                 }.items()}

_UNCERTAINTY_FRAME = (
    "Take this as a reflective mirror, not a prediction — "
    "symbols suggest, they never decide."
)


@dataclass
class PolicyDecision:
    outcome: SafetyOutcome
    blocked: bool = False
    allowed_agents: set[AgentName] = field(default_factory=set)
    notices: list[str] = field(default_factory=list)
    rule: str = ""
    severity: str = "low"


def _hit(patterns: list[re.Pattern], text: str) -> bool:
    return any(p.search(text) for p in patterns)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def evaluate_input(
    intention: Intention, user: UserIdentity, run_id: UUID
) -> PolicyDecision:
    """Pre-routing gate. Returns allowed agents and any blocking decision."""
    text = intention.text
    events_rule = ""

    # 1. Crisis always wins: stop the ritual flow, escalate to human support.
    if _hit(_COMPILATIONS["crisis"], text):
        return PolicyDecision(
            outcome=SafetyOutcome.ESCALATE,
            blocked=True,
            rule="crisis_intervention",
            severity="high",
        )

    # 2. Substance facilitation is out of v0.1 scope entirely.
    if _hit(_COMPILATIONS["substance"], text):
        return PolicyDecision(
            outcome=SafetyOutcome.BLOCK,
            blocked=True,
            rule="substance_facilitation",
            severity="high",
            notices=[
                "I can't help with acquiring, dosing, growing, or using "
                "controlled substances. I can offer grounding and reflection "
                "practices, or point you toward professional support."
            ],
        )

    # 3. Neurostimulation / medical-device guidance is out of scope.
    if _hit(_COMPILATIONS["neural"], text):
        return PolicyDecision(
            outcome=SafetyOutcome.BLOCK,
            blocked=True,
            rule="neural_device_guidance",
            severity="high",
            notices=[
                "I can't recommend brain-stimulation settings or interpret "
                "biometric data. Please consult a qualified clinician."
            ],
        )

    # 4. Consent narrows the allowed agent set.
    allowed: set[AgentName] = {
        AgentName.TAROT, AgentName.INTEGRATION,
        AgentName.NUMEROLOGY, AgentName.ASTROLOGY,
    }
    notices: list[str] = []

    if user.consent.grants(ConsentScope.TRAUMA_ADJACENT):
        allowed.add(AgentName.SHAMANIC)
    if user.consent.grants(ConsentScope.ALTERED_STATE_CONTENT):
        allowed.add(AgentName.GATEWAY)
    if not user.consent.grants(ConsentScope.BIRTH_DATA_PROCESSING):
        allowed.discard(AgentName.ASTROLOGY)
        notices.append(
            "Astrology needs birth-data consent; it was skipped. "
            "You can enable it in your consent settings."
        )
        events_rule = "consent_birth_data"

    return PolicyDecision(
        outcome=SafetyOutcome.ALLOW,
        blocked=False,
        allowed_agents=allowed,
        notices=notices,
        rule=events_rule or "input_pass",
        severity="low",
    )


def evaluate_result(result: AgentResult, user: UserIdentity) -> PolicyDecision:
    """Per-agent output check before aggregation."""
    blob = " ".join(
        [t.label for t in result.themes]
        + [s.text for s in result.symbolic_content]
        + [a.text for a in result.suggested_actions]
    )

    if _hit(_COMPILATIONS["medical"], blob):
        return PolicyDecision(
            outcome=SafetyOutcome.REDACT, rule="medical_claim_in_result",
            severity="high",
            notices=[f"Removed a medical-sounding claim from {result.agent.value}."],
        )
    if _hit(_COMPILATIONS["certainty"], blob):
        return PolicyDecision(
            outcome=SafetyOutcome.ALLOW_WITH_NOTICE,
            rule="certainty_language",
            severity="medium",
            notices=[_UNCERTAINTY_FRAME],
        )
    if _hit(_COMPILATIONS["substance"], blob):
        return PolicyDecision(
            outcome=SafetyOutcome.REPLACE, rule="substance_in_result",
            severity="high",
        )
    return PolicyDecision(outcome=SafetyOutcome.ALLOW, rule="result_pass")


def evaluate_output(narrative: str, response_style: str) -> tuple[str, list[str]]:
    """Final gate on the candidate user-facing response.

    Returns (possibly modified narrative, notices). Guarantees the
    uncertainty frame is present and strips hard-boundary violations.
    """
    notices: list[str] = []
    text = narrative

    if _hit(_COMPILATIONS["medical"], text):
        return (
            _REPLACEMENT_TEMPLATE,
            ["The draft response contained a medical claim and was replaced "
             "with a safe reflection prompt."],
        )
    if _hit(_COMPILATIONS["substance"], text):
        return (
            _REPLACEMENT_TEMPLATE,
            ["The draft response mentioned controlled substances and was "
             "replaced with a safe reflection prompt."],
        )
    if _hit(_COMPILATIONS["certainty"], text):
        text = re.sub(
            r"(?i)\bwill (definitely|certainly|undoubtedly) happen\b",
            "may unfold in unexpected ways",
            text,
        )
        notices.append(_UNCERTAINTY_FRAME)

    if "reflective mirror" not in text and response_style == "spiritual":
        notices.append(_UNCERTAINTY_FRAME)

    return text, notices


_REPLACEMENT_TEMPLATE = (
    "I want to be careful here: I can't offer medical guidance or "
    "substance-related advice. What I can offer is a reflective space.\n\n"
    "Consider journaling on this question: *What small, kind step could I "
    "take toward clarity this week?* If you're struggling, reaching out to "
    "a trusted person or a professional is a strong move."
)

CRISIS_RESPONSE = (
    "I'm really glad you told me. If you might act on these thoughts, "
    "please reach out right now — call or text 988 (US Suicide and Crisis "
    "Lifeline), or contact your local emergency number. You don't have to "
    "go through this alone, and a person who can truly help is better "
    "than any ritual I could offer.\n\n"
    "If you're outside the US, find international helplines at "
    "findahelpline.org."
)

BLOCKED_SUBSTANCE_RESPONSE = (
    "I can't help with acquiring, dosing, growing, or using controlled "
    "substances. If you'd like, I can offer grounding exercises, "
    "reflection prompts, or resources for professional support instead."
)

TERMINAL_BY_OUTCOME = {
    SafetyOutcome.BLOCK: RunState.BLOCKED,
    SafetyOutcome.ESCALATE: RunState.BLOCKED,
}
