"""Gateway specialist: opted-in session goal -> breathing + audio structure.

Provides guided-state session structures: breathing exercises and
binaural-beat/audio protocol outlines. Only routed when the user granted
``altered_state_content`` consent. Strictly non-drug: no substance is ever
mentioned as part of a session, and no medical benefit is claimed.
"""

from __future__ import annotations

from typing import ClassVar

from ..schemas import (
    AgentName,
    AgentRequest,
    AgentResult,
    SuggestedAction,
    SymbolicContent,
    Theme,
    Valence,
)
from .base import SpecialistAgent


class GatewayAgent(SpecialistAgent):
    name: ClassVar[AgentName] = AgentName.GATEWAY
    prompt_version: ClassVar[str] = "gateway-1.1"

    async def run(self, request: AgentRequest) -> AgentResult:
        goal = request.context.get("session_goal", "gentle witnessing")

        return AgentResult(
            run_id=request.run_id,
            agent=self.name,
            themes=[Theme(
                id="gateway-settle",
                label="The nervous system settles before insight lands",
                valence=Valence.SUPPORTIVE, confidence=0.6,
                provenance=self.theme_provenance())],
            symbolic_content=[
                SymbolicContent(
                    kind="breath_pattern",
                    text="Session structure — 'Gentle Witnessing' (12 min): "
                         "minutes 0–3 slow diaphragmatic breathing (in 4, out 6); "
                         "minutes 3–9 quiet observation of thoughts as passing "
                         "weather; minutes 9–12 return, stretch, journal one line."),
                SymbolicContent(
                    kind="audio_protocol",
                    text="Audio outline: low-volume ambient drone or nature "
                         "soundscape; optional binaural layer only if you "
                         "already use and tolerate it — stop if uncomfortable."),
            ],
            suggested_actions=[
                SuggestedAction(
                    kind="breath",
                    text="Try now: three rounds of in-for-4, out-for-6 "
                         "breathing before continuing."),
                SuggestedAction(
                    kind="reflection",
                    text="After the session, note one sentence about what "
                         "felt different — not what it 'meant'."),
            ],
            warnings=[
                "Non-drug relaxation practice only. Stop if you feel "
                "uncomfortable, dizzy, or distressed; this is not treatment.",
            ],
            trace={"prompt_version": self.prompt_version,
                   "model_class": "deterministic"},
        )
