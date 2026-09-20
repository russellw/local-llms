"""Deciding whether and when to try again. See SPEC.md."""

from .classify import classify, RETRYABLE, THROTTLED, FATAL


class RetryPolicy:
    def __init__(self, base_delay, max_delay, max_attempts, max_elapsed, rng):
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.max_attempts = max_attempts
        self.max_elapsed = max_elapsed
        self.rng = rng

    def next_delay(self, attempt, status, retry_after=None, elapsed=0.0, message=""):
        """Seconds to wait before the next try, or None if there must not be one."""
        kind = classify(status, message)
        if kind == FATAL:
            return None
        if attempt > self.max_attempts:
            return None

        if kind == THROTTLED and retry_after is not None:
            delay = retry_after
        else:
            ceiling = self.base_delay * 2 ** (attempt + 1)
            delay = self.rng.uniform(0, ceiling)
            delay = min(delay, self.max_delay)

        if elapsed > self.max_elapsed:
            return None
        return delay
