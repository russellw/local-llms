"""Deciding what kind of failure happened. See SPEC.md."""

RETRYABLE = "retryable"
THROTTLED = "throttled"
FATAL = "fatal"

_RETRYABLE_STATUSES = {408, 500, 502, 503, 504}
_NETWORK_HINTS = ("timeout", "reset")


def classify(status, message=""):
    """Classify a failed request."""
    if status is None:
        text = (message or "").lower()
        if any(h in text for h in _NETWORK_HINTS):
            return RETRYABLE
        return FATAL
    if status == 429:
        # Throttling has its own delay rule; treating it as fatal means the
        # code that honours retry_after is never reached.
        return THROTTLED
    if status in _RETRYABLE_STATUSES:
        return RETRYABLE
    return FATAL
