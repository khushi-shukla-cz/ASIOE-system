import asyncio

import pytest

from core.errors import RequestTimeoutError
from core.resilience import run_with_resilience


def test_run_with_resilience_retries_transient_errors_then_succeeds():
    state = {"attempts": 0}

    async def flaky_operation():
        state["attempts"] += 1
        if state["attempts"] < 3:
            raise ValueError("transient failure")
        return "ok"

    result = asyncio.run(
        run_with_resilience(
            operation_name="test.resilience.retry",
            func=flaky_operation,
            timeout_seconds=1,
            retries=3,
            retry_on=(ValueError,),
        )
    )

    assert result == "ok"
    assert state["attempts"] == 3


def test_run_with_resilience_raises_timeout_error():
    async def slow_operation():
        await asyncio.sleep(0.05)
        return "late"

    with pytest.raises(RequestTimeoutError):
        asyncio.run(
            run_with_resilience(
                operation_name="test.resilience.timeout",
                func=slow_operation,
                timeout_seconds=0.01,
                retries=1,
            )
        )
