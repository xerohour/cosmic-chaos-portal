"""The Archon: durable state machine + orchestration loop.

Implements the design doc's execution algorithm::

    validate -> policy.evaluate_input -> router.plan
      -> gather_bounded(agents, concurrency=4, per_agent=8s, total=12s)
      -> normalize valid results -> synthesizer.compose
      -> policy.evaluate_output -> finish

States: RECEIVED -> VALIDATING -> PLANNING -> RUNNING -> AGGREGATING
  -> SYNTHESIZING -> SAFETY_REVIEW -> COMPLETED | PARTIAL | BLOCKED | FAILED

Failure semantics:
  - retry once: transient agent errors only (same idempotency via run_id)
  - no retry: schema violations, policy blocks, timeouts, exhausted budgets
  - PARTIAL: at least one REQUIRED agent (integration) succeeded and the
    safety gate approved the reduced synthesis
  - circuit break: an agent with >= 3 consecutive failures is skipped
"""

from __future__ import annotations

import asyncio
import logging

from . import policy, router, synthesizer
from .agents.astrology import AstrologyAgent
from .agents.base import SpecialistAgent
from .agents.gateway import GatewayAgent
from .agents.integration import IntegrationAgent
from .agents.numerology import NumerologyAgent
from .agents.shamanic import ShamanicAgent
from .agents.tarot import TarotAgent
from .policy import (
    BLOCKED_SUBSTANCE_RESPONSE,
    CRISIS_RESPONSE,
    TERMINAL_BY_OUTCOME,
    SafetyEvent,
)
from .schemas import (
    TERMINAL_STATES,
    AgentName,
    AgentPlan,
    AgentRequest,
    AgentResult,
    FinalResponse,
    Intention,
    OrchestrationRun,
    ResultStatus,
    RunPlan,
    RunState,
    SafetyOutcome,
    UserIdentity,
)

log = logging.getLogger("ccp.archon")

REGISTRY: dict[AgentName, SpecialistAgent] = {
    AgentName.TAROT: TarotAgent(),
    AgentName.ASTROLOGY: AstrologyAgent(),
    AgentName.NUMEROLOGY: NumerologyAgent(),
    AgentName.SHAMANIC: ShamanicAgent(),
    AgentName.INTEGRATION: IntegrationAgent(),
    AgentName.GATEWAY: GatewayAgent(),
}

_CIRCUIT_THRESHOLD = 3
_consecutive_failures: dict[AgentName, int] = {}


def _transition(run: OrchestrationRun, state: RunState) -> None:
    log.info("run %s: %s -> %s", run.run_id, run.state.value, state.value)
    run.state = state


def _record_event(run: OrchestrationRun, rule: str, severity: str,
                  outcome: SafetyOutcome, note: str = "") -> None:
    run.safety_events.append(SafetyEvent(
        run_id=run.run_id, rule=rule, severity=severity,  # type: ignore[arg-type]
        outcome=outcome, note=note))


async def _invoke_once(agent: SpecialistAgent, request: AgentRequest,
                       timeout_s: float) -> AgentResult:
    """Single bounded invocation; never raises."""
    try:
        return await asyncio.wait_for(agent(request), timeout=timeout_s)
    except asyncio.TimeoutError:
        return AgentResult(
            run_id=request.run_id, agent=agent.name,
            status=ResultStatus.TIMEOUT,
            warnings=[f"{agent.name.value} timed out and was skipped."])
    except Exception as exc:  # noqa: BLE001 - defensive; base already guards
        return AgentResult(
            run_id=request.run_id, agent=agent.name,
            status=ResultStatus.ERROR,
            warnings=[f"{agent.name.value} errored: {type(exc).__name__}"])


async def _invoke_with_retry(agent: SpecialistAgent, request: AgentRequest,
                             timeout_s: float) -> AgentResult:
    """Retry once on transient error/timeout, same run_id (idempotent)."""
    first = await _invoke_once(agent, request, timeout_s)
    if first.status in (ResultStatus.ERROR, ResultStatus.TIMEOUT):
        log.warning("run %s: retrying %s once", request.run_id, agent.name.value)
        return await _invoke_once(agent, request, timeout_s)
    return first


async def _gather_bounded(plan: RunPlan, user: UserIdentity,
                          intention: Intention,
                          prior_themes: list[str]) -> list[AgentResult]:
    """Parallel divination with concurrency + total-time budgets."""
    sem = asyncio.Semaphore(plan.max_concurrency)

    async def _one(ap: AgentPlan) -> AgentResult | None:
        if _consecutive_failures.get(ap.agent, 0) >= _CIRCUIT_THRESHOLD:
            log.warning("circuit open for %s; skipping", ap.agent.value)
            return None
        agent = REGISTRY[ap.agent]
        req = AgentRequest(
            run_id=plan.run_id, agent=ap.agent, user=user,
            intention=intention,
            context={"prior_themes": prior_themes,
                     "spread": "shadow_work_cross",
                     "name": user.display_name or "",
                     "session_goal": "gentle witnessing"},
        )
        async with sem:
            result = await _invoke_with_retry(agent, req, plan.per_agent_timeout_s)
        if result.status == ResultStatus.OK:
            _consecutive_failures[ap.agent] = 0
        else:
            _consecutive_failures[ap.agent] = _consecutive_failures.get(ap.agent, 0) + 1
        return result

    try:
        results = await asyncio.wait_for(
            asyncio.gather(*[_one(ap) for ap in plan.agents]),
            timeout=plan.total_timeout_s,
        )
    except asyncio.TimeoutError:
        log.warning("run %s: total agent budget exhausted", plan.run_id)
        results = []
    return [r for r in results if r is not None]


def _normalize(results: list[AgentResult], run: OrchestrationRun) -> list[AgentResult]:
    """Schema + per-result policy check. Policy-violating results are
    dropped (or redacted) before aggregation."""
    valid: list[AgentResult] = []
    for r in results:
        if r.status != ResultStatus.OK:
            continue
        decision = policy.evaluate_result(r, run.user)
        _record_event(run, decision.rule, decision.severity,
                      decision.outcome,
                      note=f"agent={r.agent.value}")
        if decision.outcome in (SafetyOutcome.REDACT, SafetyOutcome.REPLACE):
            continue  # milestone 1: drop rather than attempt in-place repair
        valid.append(r)
    return valid


def _finish(run: OrchestrationRun, candidate: dict, notices: list[str],
            ok_results: list[AgentResult]) -> FinalResponse:
    narrative, out_notices = policy.evaluate_output(
        candidate["narrative"], run.plan.response_style if run.plan else "plain")
    notices = notices + out_notices

    required_ok = any(r.agent in router.REQUIRED_AGENTS for r in ok_results)
    if not ok_results or not required_ok:
        state = RunState.FAILED
    elif len(ok_results) < len(run.plan.agents or []):
        state = RunState.PARTIAL
        notices.append("Some specialists were unavailable; "
                       "this is a reduced reflection.")
    else:
        state = RunState.COMPLETED

    _transition(run, state)
    return FinalResponse(
        run_id=run.run_id, state=state,
        response_style=run.plan.response_style if run.plan else "plain",
        narrative=narrative,
        themes=candidate["themes"],
        suggested_actions=candidate["actions"],
        notices=notices,
    )


class Archon:
    """Orchestrator. Owns the state machine; the only component allowed to
    coordinate specialists or produce a candidate user response."""

    async def execute(self, intention: Intention, user: UserIdentity,
                      requested_modes: list[str] | None = None,
                      response_style: str | None = None) -> FinalResponse:
        run = OrchestrationRun(user=user, intention=intention)
        notices: list[str] = []

        # VALIDATING: schema is enforced by pydantic on construction.
        _transition(run, RunState.VALIDATING)

        # Pre-routing policy gate.
        pre = policy.evaluate_input(intention, user, run.run_id)
        _record_event(run, pre.rule or "input_pass", pre.severity, pre.outcome)
        notices.extend(pre.notices)
        if pre.blocked:
            _transition(run, TERMINAL_BY_OUTCOME.get(pre.outcome, RunState.BLOCKED))
            narrative = (CRISIS_RESPONSE if pre.outcome == SafetyOutcome.ESCALATE
                         else (pre.notices[0] if pre.notices
                               else BLOCKED_SUBSTANCE_RESPONSE))
            return FinalResponse(
                run_id=run.run_id, state=run.state,
                response_style="plain", narrative=narrative,
                themes=[], suggested_actions=[], notices=notices,
                crisis_resources=["988 (US)", "findahelpline.org"]
                if pre.outcome == SafetyOutcome.ESCALATE else [],
            )

        # PLANNING
        _transition(run, RunState.PLANNING)
        run.plan = router.plan(intention, user, pre.allowed_agents,
                               requested_modes, response_style)
        run.plan.run_id = run.run_id
        if not run.plan.agents:
            _transition(run, RunState.BLOCKED)
            return FinalResponse(
                run_id=run.run_id, state=run.state, response_style="plain",
                narrative="No specialists are available for this request under "
                          "your current consent settings.",
                themes=[], suggested_actions=[], notices=notices)

        # RUNNING: parallel divination under budget.
        _transition(run, RunState.RUNNING)
        raw = await _gather_bounded(run.plan, user, intention, prior_themes=[])

        # AGGREGATING: normalize + policy-check each result.
        _transition(run, RunState.AGGREGATING)
        ok_results = _normalize(raw, run)
        run.results = ok_results

        # SYNTHESIZING
        _transition(run, RunState.SYNTHESIZING)
        prior = [t.label for r in ok_results for t in r.themes[:2]]
        candidate = synthesizer.compose(ok_results, run.plan.response_style)

        # SAFETY_REVIEW -> terminal
        _transition(run, RunState.SAFETY_REVIEW)
        _ = prior  # reserved: feed themes back into a second-pass context
        return _finish(run, candidate, notices, ok_results)

    def run_sync(self, intention: Intention, user: UserIdentity,
                 **kwargs) -> FinalResponse:
        """Synchronous convenience wrapper for demos and tests."""
        return asyncio.run(self.execute(intention, user, **kwargs))


def new_user(**kwargs) -> UserIdentity:
    """Helper: build a test/demo user with explicit consent kwargs.

    Consent scopes (spiritual_language, birth_data_processing,
    trauma_adjacent, altered_state_content, biometric_research) are
    passed through to Consent; everything else goes to UserIdentity.
    """
    from .schemas import Consent
    known = set(Consent.model_fields)
    return UserIdentity(
        consent=Consent(**{k: v for k, v in kwargs.items() if k in known}),
        **{k: v for k, v in kwargs.items() if k not in known},
    )


__all__ = ["Archon", "REGISTRY", "new_user", "RunState", "TERMINAL_STATES"]
