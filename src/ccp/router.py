"""Intention router: turns an intention's tags into an agent plan.

The router intersects tag-implied specialists with the policy's allowed
agent set (consent + pre-routing checks). Agents the user asked for by name
(``requested_modes``) are honored only if policy allows them.

Tag → agent affinity is a reviewable mapping, not model behavior.
"""

from __future__ import annotations

from .schemas import (
    AgentName,
    AgentPlan,
    Intention,
    RunPlan,
    UserIdentity,
)

# Deterministic tag affinity. Keep narrow: each specialist gets invoked only
# for the domains it is designed to serve.
TAG_AFFINITY: dict[str, list[AgentName]] = {
    "shadow_work": [
        AgentName.TAROT, AgentName.SHAMANIC,
        AgentName.INTEGRATION, AgentName.GATEWAY,
    ],
    "relationship": [
        AgentName.TAROT, AgentName.SHAMANIC, AgentName.INTEGRATION,
    ],
    "career": [
        AgentName.TAROT, AgentName.NUMEROLOGY, AgentName.INTEGRATION,
    ],
    "decision": [
        AgentName.TAROT, AgentName.NUMEROLOGY, AgentName.INTEGRATION,
    ],
    "purpose": [
        AgentName.NUMEROLOGY, AgentName.SHAMANIC, AgentName.INTEGRATION,
    ],
    "timing": [
        AgentName.ASTROLOGY, AgentName.TAROT, AgentName.INTEGRATION,
    ],
    "grief": [AgentName.INTEGRATION, AgentName.SHAMANIC],
    "creativity": [AgentName.TAROT, AgentName.GATEWAY, AgentName.INTEGRATION],
    "reflection": [AgentName.INTEGRATION],
}

PROMPT_VERSIONS: dict[AgentName, str] = {
    AgentName.TAROT: "tarot-1.3",
    AgentName.ASTROLOGY: "astrology-1.0",
    AgentName.NUMEROLOGY: "numerology-1.1",
    AgentName.SHAMANIC: "shamanic-1.2",
    AgentName.INTEGRATION: "integration-1.4",
    AgentName.GATEWAY: "gateway-1.1",
}

# Agents that must succeed (when selected) for a COMPLETED rather than
# PARTIAL outcome. Integration is the harm-reduction anchor.
REQUIRED_AGENTS = {AgentName.INTEGRATION}


def plan(
    intention: Intention,
    user: UserIdentity,
    allowed_agents: set[AgentName],
    requested_modes: list[str] | None = None,
    response_style: str | None = None,
) -> RunPlan:
    """Build the run plan for an intention.

    ``requested_modes`` may name agents explicitly (e.g. ["tarot",
    "reflection"]); unknown or disallowed names are ignored.
    """
    selected: list[AgentName] = []

    # 1. Tag affinity.
    for tag in intention.tags:
        for agent in TAG_AFFINITY.get(tag, []):
            if agent not in selected:
                selected.append(agent)

    # 2. Explicitly requested agents (policy-gated).
    for mode in requested_modes or []:
        try:
            agent = AgentName(mode)
        except ValueError:
            continue
        if agent not in selected:
            selected.append(agent)

    # 3. Policy intersection: consent and pre-routing checks win.
    selected = [a for a in selected if a in allowed_agents]

    # 4. Always anchor on the integration agent when anything is selected.
    if selected and AgentName.INTEGRATION not in selected:
        selected.append(AgentName.INTEGRATION)

    style = response_style or (
        "spiritual" if user.consent.spiritual_language else "plain"
    )

    return RunPlan(
        agents=[
            AgentPlan(agent=a, prompt_version=PROMPT_VERSIONS[a])
            for a in selected
        ],
        response_style=style,  # type: ignore[arg-type]
    )
