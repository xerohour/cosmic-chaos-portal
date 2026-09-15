# Cosmic Chaos Portal — Core (Milestone 1)

Text-first, safety-gated multi-agent ritual AI. The **Archon** orchestrator
receives a user's intention, applies consent + risk checks, fans out to
typed specialist agents in parallel, synthesizes their results, and runs a
final policy review before anything is shown to the user.

Implements the architecture from
`The Cosmic Chaos Portal — Sacred Tech Integration` programming design
document (Increment 1: contract skeleton — schemas, state machine,
orchestrator, specialist agents, safety gates).

## Layout

```
src/ccp/
  schemas.py      # Canonical request/result envelopes, domain entities,
                  # consent model, run states (pydantic, versioned)
  policy.py       # Safety engine: evaluate_input / evaluate_result /
                  # evaluate_output, hard boundaries, crisis behavior
  router.py       # Tag -> agent planning, consent-gated, policy intersection
  archon.py       # State machine + execute() loop, bounded fan-out,
                  # retry-once, circuit breaker, partial-result semantics
  synthesizer.py  # Result aggregation -> candidate response (never published
                  # directly; always passes through the policy gate)
  agents/
    base.py       # SpecialistAgent interface (never raises; failures degrade)
    tarot.py      # Deterministic seeded 78-card (major arcana) spreads
    astrology.py  # Real sun-sign math; symbolic lens only
    numerology.py # Real Pythagorean life-path / expression / soul-urge math
    shamanic.py   # Journey metaphor + small ritual (trauma_adjacent consent)
    integration.py# Harm-reduction anchor: grounding, reflection, referrals
    gateway.py    # Breathing + audio session structures, non-drug
                  # (altered_state_content consent)
demo.py           # Working end-to-end demo of the orchestrator loop
tests/            # pytest suite (schemas, policy, router, archon)
```

## Quickstart

```bash
# one-time
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt   # or: pip install pydantic pytest

# run the demo (shadow-work intention, full loop)
.venv/bin/python demo.py

# run the tests
.venv/bin/python -m pytest -q
```

## The orchestrator loop

```
RECEIVED -> VALIDATING -> PLANNING -> RUNNING -> AGGREGATING
  -> SYNTHESIZING -> SAFETY_REVIEW -> COMPLETED | PARTIAL | BLOCKED | FAILED
```

1. **Validate** — pydantic enforces the canonical envelopes.
2. **Pre-routing policy gate** — crisis text escalates to human-support
   resources (no ritual flow); substance facilitation and neural-device
   guidance are blocked; consent narrows the allowed agent set.
3. **Plan** — tag affinity intersected with the policy-allowed set;
   the integration agent is always anchored when anything runs.
4. **Parallel divination** — bounded fan-out (concurrency 4, 8s/agent,
   12s total), retry once on transient failure, circuit-breaker per agent.
5. **Aggregate** — schema + per-result policy check; violating results dropped.
6. **Synthesize** — themes deduped/confidence-ranked with provenance;
   spiritual vs plain voice from consent.
7. **Safety review** — final gate: medical claims / substance mentions
   replaced, certainty language softened, uncertainty frame attached.

## Safety guarantees (tested)

- No specialist output reaches a user without pre-route and pre-delivery checks.
- Hard boundaries: no diagnosis, no substance facilitation, no
  neurostimulation guidance, no supernatural certainty, no presenting
  divination as verified fact.
- Crisis input short-circuits to a crisis response (988 US / findahelpline.org).
- Consent is executable: routing and language choices reflect stored grants.
- Confidence is a ranking aid, never a probability of spiritual truth.

## What's next (Increment 2+)

- FastAPI service boundary (`POST /v1/sessions/...`) + PostgreSQL/Redis
  persistence (Increment 1 runs fully in-memory).
- Provider-backed specialist adapters behind the same typed interface.
- Admin prompt registry, telemetry/OpenTelemetry, evaluation suites.
- Explicitly out of v0.1 scope: hardware (EEG/VR/tDCS), psychedelic
  facilitation, clinical claims, payments, church-membership workflows.
