"""Synthesizer: turns validated specialist results into a candidate response.

The synthesizer writes prose *ingredients* for the policy gate — it never
publishes directly. It merges themes (deduped by id, confidence-ranked),
carries provenance, and adapts framing to the response style:

- ``spiritual``: mythic/reflective voice, only when consent allows it.
- ``plain``:    direct, non-mythic voice. Always available.

Uncertainty framing is injected here and re-verified by the policy gate.
"""

from __future__ import annotations

from .schemas import AgentResult, SuggestedAction, Theme


def _dedupe_themes(results: list[AgentResult]) -> list[Theme]:
    seen: dict[str, Theme] = {}
    for r in results:
        for t in r.themes:
            if t.id not in seen or t.confidence > seen[t.id].confidence:
                seen[t.id] = t
    return sorted(seen.values(), key=lambda t: t.confidence, reverse=True)


def _dedupe_actions(results: list[AgentResult]) -> list[SuggestedAction]:
    seen: dict[str, SuggestedAction] = {}
    for r in results:
        for a in r.suggested_actions:
            key = a.text.strip().lower()
            if key not in seen:
                seen[key] = a
    return list(seen.values())[:6]


def compose(results: list[AgentResult], response_style: str) -> dict:
    """Return a candidate response dict for the policy gate."""
    themes = _dedupe_themes(results)
    actions = _dedupe_actions(results)

    theme_lines = "\n".join(
        f"- {t.label} ({t.valence.value}; from {t.provenance or 'unknown'})"
        for t in themes[:6]
    )
    symbol_lines = "\n".join(
        f"- [{s.kind}] {s.text}"
        for r in results for s in r.symbolic_content[:3]
    )
    action_lines = "\n".join(f"- ({a.kind}) {a.text}" for a in actions)

    if response_style == "spiritual":
        voice_open = (
            "Here is what the currents show — read it as a reflective "
            "mirror, not a verdict."
        )
    else:
        voice_open = (
            "Here is a structured reflection on your question — take it as "
            "prompts for thought, not conclusions."
        )

    narrative = (
        f"{voice_open}\n\n"
        f"## Themes that surfaced\n{theme_lines or '- (none)'}\n\n"
        f"## Symbolic material\n{symbol_lines or '- (none)'}\n\n"
        f"## Practices to try\n{action_lines or '- (none)'}"
    )
    return {
        "narrative": narrative,
        "themes": themes,
        "actions": actions,
        "contributing_agents": sorted({r.agent.value for r in results}),
    }
