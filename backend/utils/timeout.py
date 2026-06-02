from __future__ import annotations

import signal
from contextlib import contextmanager


class TimeoutException(Exception):
    pass


@contextmanager
def timeout(seconds: int):
    def _handle(signum, frame):
        raise TimeoutException("operation timed out")

    old = signal.getsignal(signal.SIGALRM)
    signal.signal(signal.SIGALRM, _handle)
    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.signal(signal.SIGALRM, old)
        signal.alarm(0)
