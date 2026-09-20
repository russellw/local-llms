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
        # max_attempts counts tries, and `attempt` is zero-based: after the
        # failure of the last permitted try there is no delay.
        if attempt >= self.max_attempts - 1:
            return None

        if kind == THROTTLED and retry_after is not None:
            delay = min(retry_after, self.max_delay)
        else:
            # Capped first, jittered within the cap -- the other order changes
            # the distribution.
            ceiling = min(self.base_delay * 2 ** attempt, self.max_delay)
            delay = self.rng.uniform(0, ceiling)

        # The budget includes the delay about to be waited. Landing exactly on
        # max_elapsed is allowed; going past it is not.
        if elapsed + delay > self.max_elapsed:
            return None
        return delay
