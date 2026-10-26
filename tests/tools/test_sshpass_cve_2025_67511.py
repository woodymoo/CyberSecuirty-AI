"""Regression tests for CVE-2025-67511.

Command injection in ``run_ssh_command_with_credentials``. In CAI <= 0.5.9 only
``password`` and ``command`` were shell-escaped, leaving ``host``, ``username``
and ``port`` injectable (CWE-77, CVSS 9.6/9.7). See GHSA-4c65-9gqf-4w8h.

These tests drive the real tool through its public ``on_invoke_tool`` entry
point and capture the command string handed to ``run_command``, asserting that
attacker-controlled ``host``/``username``/``port`` cannot break out of their
intended argument. They are written to FAIL against the pre-patch code and pass
against the current ``shlex.quote`` + integer-validated implementation.
"""

from __future__ import annotations

import json
import shlex
from typing import Any

import pytest

from cai.sdk.agents import RunContextWrapper
from cai.tools.command_and_control import sshpass as sshpass_module
from cai.tools.command_and_control.sshpass import run_ssh_command_with_credentials

# A marker a successful injection would run as its own command.
INJECTION = "; touch /tmp/pwned_cve_2025_67511 ;"


@pytest.fixture
def captured(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Replace run_command so nothing executes; record the built command."""
    seen: list[str] = []

    def _fake_run_command(cmd: str, *args: Any, **kwargs: Any) -> str:
        seen.append(cmd)
        return "ok"

    monkeypatch.setattr(sshpass_module, "run_command", _fake_run_command)
    return seen


async def _invoke(**kwargs: Any) -> str:
    return await run_ssh_command_with_credentials.on_invoke_tool(
        RunContextWrapper(None), json.dumps(kwargs)
    )


def _tokens_have_no_injected_command(command: str) -> None:
    """A shell parsing `command` must not see the marker as its own command."""
    tokens = shlex.split(command)
    assert "touch" not in tokens, f"injection broke out into: {tokens}"
    assert ";" not in tokens, f"injection broke out into: {tokens}"
    # The marker survives only as inert text inside a single quoted argument.
    assert any("pwned_cve_2025_67511" in t for t in tokens)


@pytest.mark.asyncio
async def test_host_injection_is_neutralized(captured: list[str]) -> None:
    await _invoke(
        host=f"10.0.0.1{INJECTION}",
        username="root",
        password="pw",
        command="id",
    )
    assert captured, "run_command was not reached"
    _tokens_have_no_injected_command(captured[0])


@pytest.mark.asyncio
async def test_username_injection_is_neutralized(captured: list[str]) -> None:
    await _invoke(
        host="10.0.0.1",
        username=f"root{INJECTION}",
        password="pw",
        command="id",
    )
    assert captured, "run_command was not reached"
    _tokens_have_no_injected_command(captured[0])


@pytest.mark.asyncio
async def test_password_injection_is_neutralized(captured: list[str]) -> None:
    await _invoke(
        host="10.0.0.1",
        username="root",
        password=f"pw{INJECTION}",
        command="id",
    )
    assert captured, "run_command was not reached"
    _tokens_have_no_injected_command(captured[0])


@pytest.mark.asyncio
async def test_malicious_port_is_rejected_before_execution(
    captured: list[str],
) -> None:
    await _invoke(
        host="10.0.0.1",
        username="root",
        password="pw",
        command="id",
        port="22; rm -rf / #",
    )
    # The security invariant is that no command is ever built from a non-integer
    # port, whether it is rejected by the tool's int()/range guard or earlier by
    # the function_tool JSON-schema (port is typed int). Either way run_command
    # must not be reached, so we assert on that rather than a specific message.
    assert not captured, "a non-integer port must be rejected before run_command"


@pytest.mark.asyncio
@pytest.mark.parametrize("bad_port", [0, -1, 65536, 99999])
async def test_out_of_range_port_is_rejected(
    captured: list[str], bad_port: int
) -> None:
    result = await _invoke(
        host="10.0.0.1",
        username="root",
        password="pw",
        command="id",
        port=bad_port,
    )
    assert "port is not a valid integer" in result
    assert not captured


@pytest.mark.asyncio
async def test_benign_command_is_built_as_expected(captured: list[str]) -> None:
    await _invoke(
        host="10.0.0.1",
        username="root",
        password="pw",
        command="id",
        port=2222,
    )
    assert captured
    cmd = captured[0]
    # Normal flags are present and the remote command is a single quoted token.
    assert "ssh -o StrictHostKeyChecking=no" in cmd
    assert "-p 2222" in cmd
    assert shlex.split(cmd)[-1] == "id"
