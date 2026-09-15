"""Specialist agent interface.

Every specialist is a pure, deterministic function of the canonical
request envelope. Specialists never call each other and never publish
directly — results are structured ingredients for the Archon's synthesizer,
never user-facing prose.

For milestone 1 the agents are local/deterministic (the design doc's
"fake agents" increment, but with real domain logic: an actual tarot deck,
real numerology calculations, real sun-sign math). Provider-backed
implementations can replace any of these without changing the contract.
"""

from __future__ import annotations

import hashlib
from abc import ABC, abstractmethod
from typing import ClassVar

from ..schemas import AgentName, AgentRequest, AgentResult, ResultStatus


class SpecialistAgent(ABC):
    """Base class every specialist implements."""

    name: ClassVar[AgentName]
    prompt_version: ClassVar[str] = "base-1.0"

    async def __call__(self, request: AgentRequest) -> AgentResult:
        """Entry point used by the Archon. Never raises: failures become
        ``status=error`` results so the run can degrade to PARTIAL."""
        try:
            result = await self.run(request)
        except Exception as exc:  # noqa: BLE001 - degraded, not propagated
            result = AgentResult(
                run_id=request.run_id,
                agent=self.name,
                status=ResultStatus.ERROR,
                warnings=[f"{self.name.value} failed safely: {type(exc).__name__}"],
            )
        result.agent = self.name
        result.run_id = request.run_id
        result.schema_version = "1.0"
        result.trace.setdefault("prompt_version", self.prompt_version)
        return result

    @abstractmethod
    async def run(self, request: AgentRequest) -> AgentResult:
        """Produce the typed result envelope."""

    # -- helpers ----------------------------------------------------------

    @staticmethod
    def seed(request: AgentRequest, salt: str = "") -> int:
        """Deterministic, auditable seed from run_id + agent + salt."""
        digest = hashlib.sha256(
            f"{request.run_id}:{request.agent.value}:{salt}".encode()
        ).hexdigest()
        return int(digest[:16], 16)

    def theme_provenance(self) -> str:
        return f"{self.name.value}:{self.prompt_version}"
