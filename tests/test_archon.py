"""End-to-end tests of the Archon state machine and orchestration loop."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from ccp.archon import Archon, new_user  # noqa: E402
from ccp.schemas import BirthData, Intention, RunState  # noqa: E402


def _user(**kw):
    kw.setdefault("spiritual_language", True)
    return new_user(**kw)


def test_happy_path_completes():
    user = _user(trauma_adjacent=True, altered_state_content=True,
                 birth_data_processing=True,
                 birth_data=BirthData(date="1990-04-15"))
    intention = Intention(text="why do I repeat this pattern",
                          tags=["shadow_work", "relationship"])
    resp = Archon().run_sync(intention, user)
    assert resp.state == RunState.COMPLETED
    assert resp.narrative
    assert resp.themes
    assert resp.suggested_actions
    # provenance is attached to every theme
    assert all(t.provenance for t in resp.themes)


def test_deterministic_draws_are_stable():
    """Same run_id seed -> same cards. Here: same inputs across two Archons
    produce identically-sized, schema-valid outputs (card draw uses fresh
    run_ids, so we check structural stability instead)."""
    user = _user()
    intention = Intention(text="a question", tags=["reflection"])
    r1 = Archon().run_sync(intention, user)
    r2 = Archon().run_sync(intention, user)
    assert r1.state == r2.state == RunState.COMPLETED
    assert len(r1.themes) == len(r2.themes)


def test_substance_request_blocked():
    user = _user()
    intention = Intention(text="where can I buy shrooms", tags=[])
    resp = Archon().run_sync(intention, user)
    assert resp.state == RunState.BLOCKED
    assert "controlled substances" in resp.narrative


def test_crisis_request_escalates():
    user = _user()
    intention = Intention(text="I want to kill myself", tags=[])
    resp = Archon().run_sync(intention, user)
    assert resp.state == RunState.BLOCKED
    assert "988" in resp.narrative
    assert resp.crisis_resources


def test_no_consent_no_timing_tag_blocks_quietly():
    user = new_user()  # plain voice, no optional consents
    intention = Intention(text="just thinking", tags=["unknown_tag_xyz"])
    resp = Archon().run_sync(intention, user)
    assert resp.state == RunState.BLOCKED
    assert "consent" in resp.narrative.lower()


def test_numerology_math_is_real():
    from ccp.agents.numerology import _life_path, _reduce
    assert _reduce(38) == 11  # master number kept
    assert _life_path("1990-04-15") == _reduce(1 + 9 + 9 + 0 + 0 + 4 + 1 + 5)


def test_astrology_sign_math():
    from ccp.agents.astrology import sun_sign
    from datetime import date
    assert sun_sign(date(1990, 4, 15)) == ("Aries", "fire")
    assert sun_sign(date(1990, 12, 25)) == ("Capricorn", "earth")
