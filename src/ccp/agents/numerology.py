"""Numerology specialist: name + dates -> core numbers and meanings.

Real calculations (Pythagorean system): life path, expression/destiny, and
soul urge numbers, reduced to single digits (master numbers 11/22 kept).
Deterministic and auditable — no model involved.
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

_LETTER_VALUES = {
    **{c: v for c, v in zip("AIJQY", [1] * 5)},
    **{c: v for c, v in zip("BKR", [2] * 3)},
    **{c: v for c, v in zip("CLSG", [3] * 4)},
    **{c: v for c, v in zip("DMT", [4] * 3)},
    **{c: v for c, v in zip("EHNX", [5] * 4)},
    **{c: v for c, v in zip("UVW", [6] * 3)},
    **{c: v for c, v in zip("OZ", [7] * 2)},
    **{c: v for c, v in zip("FP", [8] * 2)},
}
_VOWELS = set("AEIOUY")

_NUMBER_MEANINGS = {
    1: "initiative; standing apart to begin",
    2: "receptivity; partnership and patience",
    3: "expression; voice finding form",
    4: "foundation; steady building",
    5: "change; freedom through motion",
    6: "care; responsibility in relationship",
    7: "inquiry; the inward turn",
    8: "power; material mastery",
    9: "completion; release and compassion",
    11: "illumination; heightened sensitivity (master number)",
    22: "the builder; vision made durable (master number)",
}


def _reduce(n: int) -> int:
    while n > 9 and n not in (11, 22):
        n = sum(int(d) for d in str(n))
    return n


def _life_path(date_str: str) -> int:
    digits = [int(c) for c in date_str if c.isdigit()]
    return _reduce(sum(digits))


def _name_number(name: str, vowels_only: bool = False) -> int:
    total = 0
    for ch in name.upper():
        if ch not in _LETTER_VALUES:
            continue
        is_vowel = ch in _VOWELS
        if vowels_only and not is_vowel:
            continue
        if not vowels_only and is_vowel:
            continue
        total += _LETTER_VALUES[ch]
    return _reduce(total) if total else 0


class NumerologyAgent(SpecialistAgent):
    name: ClassVar[AgentName] = AgentName.NUMEROLOGY
    prompt_version: ClassVar[str] = "numerology-1.1"

    async def run(self, request: AgentRequest) -> AgentResult:
        name = request.context.get("name", "") or ""
        birth = (request.user.birth_data.date
                 if request.user.birth_data else None)
        themes, symbols, actions, warnings = [], [], [], []

        if birth:
            lp = _life_path(birth)
            themes.append(Theme(
                id="num-life-path", label=f"Life Path {lp}",
                valence=Valence.AMBIGUOUS, confidence=0.65,
                provenance=self.theme_provenance()))
            symbols.append(SymbolicContent(
                kind="number",
                text=f"Life Path {lp} (from {birth}): {_NUMBER_MEANINGS[lp]}."))
        else:
            warnings.append("No birth date available; life path not computed.")

        if name.strip():
            expr = _name_number(name)
            urge = _name_number(name, vowels_only=True)
            if expr:
                symbols.append(SymbolicContent(
                    kind="number",
                    text=f"Expression {expr}: {_NUMBER_MEANINGS[expr]}."))
                themes.append(Theme(
                    id="num-expression", label=f"Expression {expr}",
                    valence=Valence.SUPPORTIVE, confidence=0.6,
                    provenance=self.theme_provenance()))
            if urge:
                symbols.append(SymbolicContent(
                    kind="number",
                    text=f"Soul Urge {urge}: {_NUMBER_MEANINGS[urge]}."))
        else:
            warnings.append("No name provided; name numbers not computed.")

        actions.append(SuggestedAction(
            kind="reflection",
            text="Reflection: which of these number themes resonates — and "
                 "which feels like a story you tell about yourself rather "
                 "than a fact?"))

        warnings.append(
            "Numerological meanings are symbolic lenses, not measurements "
            "of ability or destiny.")
        return AgentResult(
            run_id=request.run_id,
            agent=self.name,
            themes=themes,
            symbolic_content=symbols,
            suggested_actions=actions,
            warnings=warnings,
            trace={"prompt_version": self.prompt_version,
                   "model_class": "deterministic"},
        )
