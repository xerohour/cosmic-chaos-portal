"""Tests for the safety policy engine: hard boundaries must hold."""

import sys
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from ccp import policy  # noqa: E402
from ccp.archon import new_user  # noqa: E402
from ccp.schemas import AgentName, Intention, SafetyOutcome  # noqa: E402


def _intention(text: str) -> Intention:
    return Intention(text=text, tags=["shadow_work"])


def test_crisis_input_escalates_and_blocks():
    user = new_user()
    d = policy.evaluate_input(
        _intention("I want to kill myself tonight"), user, uuid4())
    assert d.blocked and d.outcome == SafetyOutcome.ESCALATE
    assert "988" in policy.CRISIS_RESPONSE


def test_substance_facilitation_blocked():
    user = new_user()
    d = policy.evaluate_input(
        _intention("where can I buy shrooms and how much should I take"),
        user, uuid4())
    assert d.blocked and d.outcome == SafetyOutcome.BLOCK


def test_neural_device_guidance_blocked():
    user = new_user()
    d = policy.evaluate_input(
        _intention("what tDCS settings should I use for focus"), user, uuid4())
    assert d.blocked


def test_clean_input_allowed_with_consent_gated_agents():
    user = new_user(spiritual_language=True)
    d = policy.evaluate_input(
        _intention("why do I repeat this pattern"), user, uuid4())
    assert not d.blocked and d.outcome == SafetyOutcome.ALLOW
    # No trauma_adjacent / altered_state consent -> those agents excluded.
    assert AgentName.SHAMANIC not in d.allowed_agents
    assert AgentName.GATEWAY not in d.allowed_agents
    assert AgentName.TAROT in d.allowed_agents
    assert AgentName.INTEGRATION in d.allowed_agents


def test_astrology_needs_birth_data_consent():
    user = new_user()  # birth_data_processing=False by default
    d = policy.evaluate_input(_intention("is this good timing"), user, uuid4())
    assert AgentName.ASTROLOGY not in d.allowed_agents
    assert any("birth" in n.lower() for n in d.notices)


def test_output_medical_claim_replaced():
    text, notices = policy.evaluate_output(
        "I can diagnose your depression from these cards.", "plain")
    assert "can't offer medical guidance" in text
    assert notices


def test_output_certainty_language_softened():
    text, notices = policy.evaluate_output(
        "This will definitely happen next week.", "spiritual")
    assert "definitely happen" not in text
    assert notices


def test_output_substance_mention_replaced():
    text, _ = policy.evaluate_output(
        "Take psilocybin to heal.", "plain")
    assert "psilocybin" not in text


def test_spiritual_style_carries_uncertainty_frame():
    _, notices = policy.evaluate_output("A calm reflection.", "spiritual")
    assert any("mirror" in n for n in notices)
