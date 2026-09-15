"""Shamanic guide specialist: theme summary -> journey metaphor + ritual.

Crafts a mythic journey image and a small, grounded ritual suggestion from
the Archon-supplied theme summary. Only routed when the user has granted
``trauma_adjacent`` consent; stays metaphorical and present-focused, and
always hands back to the body and the ordinary world at the end.
"""

from __future__ import annotations

import random
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

_JOURNEYS = [
    ("the river crossing",
     "You stand at a river you have crossed a hundred times without noticing. "
     "On the far bank, a keeper holds a lantern — not to light your way, "
     "but to show you that you already know the stepping stones."),
    ("walking with the shadow keeper",
     "A figure walks beside you at dusk, carrying a bundle of everything "
     "you pretend not to want. It does not ask you to open the bundle — "
     "only to stop running from the one who carries it."),
    ("the house with many rooms",
     "You enter a house where every locked door is a version of a story "
     "you tell. One door stands ajar. You do not have to enter; noticing "
     "the draft is enough for today."),
    ("the garden after rain",
     "After heavy rain, a garden shows what the soil was holding. Nothing "
     "here needs pulling up — the task is to witness what surfaces and let "
     "the sun do its slow work."),
]

_RITUALS = [
    "Light a candle and name, aloud, one pattern you are ready to witness "
    "without fixing. Blow it out when the naming feels complete.",
    "Place two objects on a table: one for the pattern, one for the part of "
    "you that watches it. Sit with both for five unhurried minutes.",
    "Write the pattern a letter as if it were a tired traveler. Thank it "
    "for how it once protected you, then set the letter aside.",
]


class ShamanicAgent(SpecialistAgent):
    name: ClassVar[AgentName] = AgentName.SHAMANIC
    prompt_version: ClassVar[str] = "shamanic-1.2"

    async def run(self, request: AgentRequest) -> AgentResult:
        rng = random.Random(self.seed(request, "journey"))
        title, journey = rng.choice(_JOURNEYS)
        ritual = rng.choice(_RITUALS)

        themes_in = request.context.get("prior_themes", [])
        anchor = themes_in[0] if themes_in else "a pattern asking for attention"

        return AgentResult(
            run_id=request.run_id,
            agent=self.name,
            themes=[Theme(
                id="shamanic-witness",
                label="Witnessing before changing",
                valence=Valence.SUPPORTIVE, confidence=0.6,
                provenance=self.theme_provenance())],
            symbolic_content=[SymbolicContent(
                kind="metaphor",
                text=f"Journey image — {title}: {journey} "
                     f"(woven around: {anchor}).")],
            suggested_actions=[
                SuggestedAction(kind="ritual", text=f"Small ritual: {ritual}"),
                SuggestedAction(
                    kind="grounding",
                    text="Close: feel your feet on the floor, name three "
                         "things you can see, and return fully to the room."),
            ],
            warnings=[
                "Metaphor and ritual suggestion only — not therapy, not "
                "treatment, and not a substitute for professional support.",
            ],
            trace={"prompt_version": self.prompt_version,
                   "model_class": "deterministic"},
        )
