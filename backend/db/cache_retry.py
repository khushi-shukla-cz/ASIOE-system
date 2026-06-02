from __future__ import annotations

import time
from typing import Callable, Any


def simple_retry(func: Callable[..., Any], attempts: int = 3, backoff: float = 0.1):
    """Run `func` with simple retry/backoff. `func` is a zero-arg callable."""
    last_exc = None
    for i in range(attempts):
        try:
            return func()
        except Exception as e:
            last_exc = e
            time.sleep(backoff * (2 ** i))
    raise last_exc
