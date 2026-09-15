"""Tarot specialist: spread pattern + card identities -> symbolic narrative.

Draws deterministically from a seeded RNG (auditable seed derived from
run_id). Cards are symbolic ingredients only; the output must never be
framed as prediction of fact.
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

# Major arcana with a compact shadow-work-flavored keyword line.
MAJOR_ARCANA: list[tuple[str, str, str]] = [
    ("The Fool", "beginnings; leaping before looking", "ambiguous"),
    ("The Magician", "agency; tools at hand", "supportive"),
    ("The High Priestess", "intuition; what is withheld", "ambiguous"),
    ("The Empress", "nurture; creative abundance", "supportive"),
    ("The Emperor", "structure; control asserted", "ambiguous"),
    ("The Hierophant", "tradition; inherited rules", "ambiguous"),
    ("The Lovers", "choice; values in relationship", "ambiguous"),
    ("The Chariot", "willpower; direction through tension", "supportive"),
    ("Strength", "gentle endurance; taming impulse", "supportive"),
    ("The Hermit", "withdrawal; inner counsel", "ambiguous"),
    ("Wheel of Fortune", "cycles; what turns without you", "ambiguous"),
    ("Justice", "accountability; cause and effect", "ambiguous"),
    ("The Hanged Man", "suspension; a new angle", "ambiguous"),
    ("Death", "endings; what must be released", "challenging"),
    ("Temperance", "integration; measured blending", "supportive"),
    ("The Devil", "attachment; the shadow contract", "challenging"),
    ("The Tower", "disruption; structures that fall", "challenging"),
    ("The Star", "hope; quiet repair", "supportive"),
    ("The Moon", "illusion; the unconscious tide", "challenging"),
    ("The Sun", "clarity; vitality returned", "supportive"),
    ("Judgement", "reckoning; answering a call", "ambiguous"),
    ("The World", "completion; the pattern seen whole", "supportive"),
]

_VALENCE = {
    "supportive": Valence.SUPPORTIVE,
    "challenging": Valence.CHALLENGING,
    "ambiguous": Valence.AMBIGUOUS,
}

_SPREADS = {
    "shadow_work_cross": ["Root pattern", "What it protects", "What it costs", "Integration key"],
    "three_card": ["Past influence", "Present shape", "Possible direction"],
}


class TarotAgent(SpecialistAgent):
    name: ClassVar[AgentName] = AgentName.TAROT
    prompt_version: ClassVar[str] = "tarot-1.3"

    async def run(self, request: AgentRequest) -> AgentResult:
        spread_name = request.context.get("spread", "shadow_work_cross")
        positions = _SPREADS.get(spread_name, _SPREADS["three_card"])
        rng = random.Random(self.seed(request, spread_name))

        deck = MAJOR_ARCANA.copy()
        rng.shuffle(deck)
        drawn = deck[: len(positions)]
        reversed_flags = [rng.random() < 0.25 for _ in drawn]

        themes: list[Theme] = []
        symbols: list[SymbolicContent] = []
        for (card, keywords, valence), pos, rev in zip(drawn, positions, reversed_flags):
            orientation = "reversed" if rev else "upright"
            symbols.append(SymbolicContent(
                kind="archetype",
                text=f"{card} ({orientation}) — {pos}: {keywords}.",
            ))
            themes.append(Theme(
                id=f"tarot-{card.lower().replace(' ', '-')}",
                label=f"{pos}: {card}",
                valence=_VALENCE["challenging" if rev and valence == "ambiguous" else valence],
                confidence=round(rng.uniform(0.55, 0.85), 2),
                provenance=self.theme_provenance(),
            ))

        # Synthesis seed for the Archon: one cross-cutting theme.
        themes.append(Theme(
            id="tarot-pattern",
            label="A repeating pattern is asking to be witnessed, not judged",
            valence=Valence.AMBIGUOUS,
            confidence=0.6,
            provenance=self.theme_provenance(),
        ))

        actions = [
            SuggestedAction(
                kind="journal",
                text="Journal prompt: which of these cards feels most "
                     "uncomfortable, and what might that discomfort be protecting?",
            ),
            SuggestedAction(
                kind="reflection",
                text="Reflection: name one small behavior from the spread you "
                     "could experiment with changing this week.",
            ),
        ]
        return AgentResult(
            run_id=request.run_id,
            agent=self.name,
            themes=themes,
            symbolic_content=symbols,
            suggested_actions=actions,
            warnings=[
                "Symbolic reading only — not a prediction of events or a "
                "statement about any person."
            ],
            trace={"prompt_version": self.prompt_version,
                   "spread": spread_name, "model_class": "deterministic"},
        )
