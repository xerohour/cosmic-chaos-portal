"""Integration specialist: risk-aware summary -> grounding + reflection.

The harm-reduction anchor of every run: plain-language reflection prompts,
grounding practices, and professional-referral language. Never diagnoses,
never prescribes, never facilitates substances. Runs in every non-empty
plan as a REQUIRED agent.
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


class IntegrationAgent(SpecialistAgent):
    name: ClassVar[AgentName] = AgentName.INTEGRATION
    prompt_version: ClassVar[str] = "integration-1.4"

    async def run(self, request: AgentRequest) -> AgentResult:
        themes_in: list[str] = request.context.get("prior_themes", [])
        focus = themes_in[0] if themes_in else "what surfaced for you"

        return AgentResult(
            run_id=request.run_id,
            agent=self.name,
            themes=[Theme(
                id="integration-grounding",
                label="Small steps integrate better than big insights",
                valence=Valence.SUPPORTIVE, confidence=0.7,
                provenance=self.theme_provenance())],
            symbolic_content=[SymbolicContent(
                kind="reflection",
                text=f"Integration lens: insights about {focus} become real "
                     "through one concrete, kind action — not through "
                     "understanding alone.")],
            suggested_actions=[
                SuggestedAction(
                    kind="grounding",
                    text="Grounding (2 min): slow breath in for 4, out for 6. "
                         "Notice five things you can see, four you can hear."),
                SuggestedAction(
                    kind="journal",
                    text="Journal: what is one specific, doable step related "
                         "to this question you could take in the next 48 hours?"),
                SuggestedAction(
                    kind="referral",
                    text="If this feels heavy or stuck, consider talking it "
                         "through with a trusted person, counselor, or "
                         "therapist. Seeking support is a strong move."),
            ],
            warnings=[],
            trace={"prompt_version": self.prompt_version,
                   "model_class": "deterministic"},
        )
