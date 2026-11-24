"""Small in-process rate limiters that protect the Gemini API quota and bill.

nginx already caps requests per IP (a coarse flood guard). These limits sit
behind it and are NAT-proof: they count per *session* and across the *whole
server*, so one noisy player, one scripted client, or one venue sharing a single
IP can't burn the model budget for everyone else.

Single uvicorn worker only (like the rest of the in-process state), so plain
dicts are safe: asyncio handlers never run these methods concurrently.
"""

import time
from collections import deque


class SlidingWindow:
    """At most `limit` hits per `window` seconds, per key (key=None → one global bucket)."""

    def __init__(self, limit: int, window: float, max_keys: int = 5000):
        self.limit = limit
        self.window = window
        self.max_keys = max_keys
        self._hits: dict[object, deque] = {}

    def check(self, key=None, now: float | None = None) -> float:
        """Record a hit. Returns 0 if allowed, else seconds until a slot frees
        (a refused hit is NOT recorded, so hammering doesn't extend the wait)."""
        if self.limit <= 0:  # 0 or negative disables the limit
            return 0.0
        now = time.monotonic() if now is None else now
        q = self._hits.setdefault(key, deque())
        cutoff = now - self.window
        while q and q[0] <= cutoff:
            q.popleft()
        if len(q) >= self.limit:
            return max(0.1, q[0] + self.window - now)
        q.append(now)
        if len(self._hits) > self.max_keys:  # bound memory: drop idle keys
            for k in [k for k, v in self._hits.items() if not v or v[-1] <= cutoff]:
                del self._hits[k]
        return 0.0


class InFlight:
    """Cap on concurrent expensive operations (each one is 1-4 model calls)."""

    def __init__(self, limit: int):
        self.limit = limit
        self.current = 0

    def acquire(self) -> bool:
        if self.limit > 0 and self.current >= self.limit:
            return False
        self.current += 1
        return True

    def release(self) -> None:
        self.current = max(0, self.current - 1)
