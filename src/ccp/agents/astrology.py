"""Astrology specialist: birth data + timestamp -> chart highlights.

Milestone 1 keeps this deliberately narrow and deterministic: real sun-sign
math from the birth date plus theme language keyed to the sign's element.
No houses, no transits-as-fact, no model-generated computations — the
design doc defers ephemeris accuracy to a later research track.
"""

from __future__ import annotations

from datetime import date
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

_SIGNS = [
    ("Capricorn", (12, 22), (1, 19), "earth"),
    ("Aquarius", (1, 20), (2, 18), "air"),
    ("Pisces", (2, 19), (3, 20), "water"),
    ("Aries", (3, 21), (4, 19), "fire"),
    ("Taurus", (4, 20), (5, 20), "earth"),
    ("Gemini", (5, 21), (6, 20), "air"),
    ("Cancer", (6, 21), (7, 22), "water"),
    ("Leo", (7, 23), (8, 22), "fire"),
    ("Virgo", (8, 23), (9, 22), "earth"),
    ("Libra", (9, 23), (10, 22), "air"),
    ("Scorpio", (10, 23), (11, 21), "water"),
    ("Sagittarius", (11, 22), (12, 21), "fire"),
]

_ELEMENT_THEMES = {
    "fire": ("direct action; naming what you want out loud", Valence.SUPPORTIVE),
    "earth": ("steady craft; what is built slowly holds", Valence.SUPPORTIVE),
    "air": ("perspective; the story can be retold", Valence.AMBIGUOUS),
    "water": ("emotional honesty; feeling before fixing", Valence.CHALLENGING),
}


def sun_sign(birth: date) -> tuple[str, str]:
    m, d = birth.month, birth.day
    for name, (m1, d1), (m2, d2), element in _SIGNS:
        if (m == m1 and d >= d1) or (m == m2 and d <= d2):
            return name, element
    return "Capricorn", "earth"  # unreachable; keeps mypy calm


class AstrologyAgent(SpecialistAgent):
    name: ClassVar[AgentName] = AgentName.ASTROLOGY
    prompt_version: ClassVar[str] = "astrology-1.0"

    async def run(self, request: AgentRequest) -> AgentResult:
        birth = request.user.birth_data.date if request.user.birth_data else None
        if not birth:
            return AgentResult(
                run_id=request.run_id,
                agent=self.name,
                warnings=["Birth data not available; chart highlights skipped."],
                trace={"prompt_version": self.prompt_version},
            )

        sign, element = sun_sign(date.fromisoformat(birth))
        theme_text, valence = _ELEMENT_THEMES[element]
        return AgentResult(
            run_id=request.run_id,
            agent=self.name,
            themes=[Theme(
                id=f"astro-{sign.lower()}",
                label=f"Sun in {sign} ({element} element)",
                valence=valence, confidence=0.6,
                provenance=self.theme_provenance())],
            symbolic_content=[SymbolicContent(
                kind="archetype",
                text=f"Sun-sign lens — {sign}: {theme_text}.")],
            suggested_actions=[SuggestedAction(
                kind="reflection",
                text=f"Reflection: where in your current question could a "
                     f"{element}-element approach ({theme_text.split(';')[0]}) help?")],
            warnings=[
                "Sun-sign highlights are symbolic prompts, not astrological "
                "determinations or life predictions.",
            ],
            trace={"prompt_version": self.prompt_version,
                   "model_class": "deterministic"},
        )
