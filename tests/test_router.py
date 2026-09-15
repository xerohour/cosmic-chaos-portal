"""Tests for the intention router."""

import sys
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from ccp import policy, router  # noqa: E402
from ccp.archon import new_user  # noqa: E402
from ccp.schemas import AgentName, Intention  # noqa: E402


def _plan_for(tags, user, requested=None, style=None):
    intention = Intention(text="test", tags=tags)
    pre = policy.evaluate_input(intention, user, uuid4())
    return router.plan(intention, user, pre.allowed_agents, requested, style)


def test_shadow_work_routes_four_agents_with_full_consent():
    user = new_user(trauma_adjacent=True, altered_state_content=True,
                    birth_data_processing=True)
    plan = _plan_for(["shadow_work"], user)
    agents = {a.agent for a in plan.agents}
    assert agents == {AgentName.TAROT, AgentName.SHAMANIC,
                      AgentName.INTEGRATION, AgentName.GATEWAY}


def test_policy_intersection_removes_unconsented_agents():
    user = new_user()  # no optional consents
    plan = _plan_for(["shadow_work"], user)
    agents = {a.agent for a in plan.agents}
    assert AgentName.SHAMANIC not in agents
    assert AgentName.GATEWAY not in agents
    assert AgentName.INTEGRATION in agents  # always anchored


def test_requested_unknown_mode_ignored():
    user = new_user()
    plan = _plan_for(["reflection"], user, requested=["nonsense", "tarot"])
    agents = {a.agent for a in plan.agents}
    assert AgentName.TAROT in agents
    assert len(agents) == 2  # tarot + integration anchor


def test_spiritual_style_requires_consent():
    plain_user = new_user()
    plan = _plan_for(["career"], plain_user)
    assert plan.response_style == "plain"

    spirit_user = new_user(spiritual_language=True)
    plan = _plan_for(["career"], spirit_user)
    assert plan.response_style == "spiritual"


def test_empty_tags_yields_empty_plan():
    user = new_user()
    plan = _plan_for(["unknown_tag_xyz"], user)
    assert plan.agents == []
