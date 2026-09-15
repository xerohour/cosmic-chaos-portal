"""Tests for typed agent contracts (schemas)."""

import sys
from pathlib import Path
from uuid import uuid4

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from ccp.schemas import (  # noqa: E402
    SCHEMA_VERSION,
    AgentName,
    AgentRequest,
    AgentResult,
    Intention,
    ResultStatus,
    RunState,
    UserIdentity,
)


def test_request_envelope_validates():
    req = AgentRequest(
        run_id=uuid4(), agent=AgentName.TAROT,
        user=UserIdentity(), intention=Intention(text="hello"),
    )
    assert req.schema_version == SCHEMA_VERSION


def test_request_rejects_unknown_schema_version():
    with pytest.raises(Exception):
        AgentRequest(
            schema_version="9.9", run_id=uuid4(), agent=AgentName.TAROT,
            user=UserIdentity(), intention=Intention(text="hello"),
        )


def test_request_rejects_oversized_intention():
    with pytest.raises(Exception):
        Intention(text="x" * 2001)


def test_result_defaults_and_bounds():
    res = AgentResult(run_id=uuid4(), agent=AgentName.TAROT)
    assert res.status == ResultStatus.OK
    assert res.schema_version == SCHEMA_VERSION


def test_theme_confidence_bounded():
    from ccp.schemas import Theme, Valence
    with pytest.raises(Exception):
        Theme(id="x", label="y", valence=Valence.SUPPORTIVE, confidence=1.5)


def test_terminal_states_cover_expected_set():
    from ccp.schemas import TERMINAL_STATES
    assert TERMINAL_STATES == {
        RunState.COMPLETED, RunState.PARTIAL,
        RunState.BLOCKED, RunState.FAILED,
    }
