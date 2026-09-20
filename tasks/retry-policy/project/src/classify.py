"""Deciding what kind of failure happened. See SPEC.md."""

RETRYABLE = "retryable"
THROTTLED = "throttled"
FATAL = "fatal"

_RETRYABLE_STATUSES = {408, 500, 502, 503, 504}


def classify(status, message=""):
    """Classify a failed request."""
    if status is None:
        text = (message or "")
        if "timeout" in text or "reset" in text:
            return RETRYABLE
        return FATAL
    if status in _RETRYABLE_STATUSES:
        return RETRYABLE
    return FATAL
