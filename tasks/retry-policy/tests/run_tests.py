"""Hidden test suite. Curated one-line failures only; never a traceback."""

import sys

from src.classify import classify, RETRYABLE, THROTTLED, FATAL
from src.policy import RetryPolicy

FAILURES = []
PASSED = 0


def check(name, fn):
    global PASSED
    try:
        fn()
    except AssertionError as e:
        FAILURES.append(f"{name}: {e}")
    except Exception as e:
        FAILURES.append(f"{name}: raised {type(e).__name__}: {e}")
    else:
        PASSED += 1


def eq(got, want, what):
    if got != want:
        raise AssertionError(f"{what} was {got!r}, expected {want!r}")


class FixedRng:
    """rng.uniform(a, b) -> a + (b - a) * frac. Deterministic on purpose."""

    def __init__(self, frac):
        self.frac = frac

    def uniform(self, a, b):
        return a + (b - a) * self.frac


def policy(frac=0.5, base=1.0, cap=30.0, attempts=5, elapsed_budget=1000.0):
    return RetryPolicy(base, cap, attempts, elapsed_budget, FixedRng(frac))


# -- classification -----------------------------------------------------

def server_errors_are_retryable():
    for s in (408, 500, 502, 503, 504):
        eq(classify(s), RETRYABLE, f"classification of {s}")


def too_many_requests_is_throttled():
    eq(classify(429), THROTTLED, "classification of 429")


def other_client_errors_are_fatal():
    for s in (400, 401, 403, 404, 422):
        eq(classify(s), FATAL, f"classification of {s}")


def success_is_fatal():
    eq(classify(200), FATAL, "classification of 200")


def network_timeout_is_retryable():
    eq(classify(None, "connection timeout"), RETRYABLE, "classification of a timeout")


def network_reset_is_retryable():
    eq(classify(None, "Connection reset by peer"), RETRYABLE, "classification of a reset")


def network_hints_are_case_insensitive():
    eq(classify(None, "TIMEOUT while reading"), RETRYABLE, "classification of an upper-case timeout")


def other_network_errors_are_fatal():
    eq(classify(None, "certificate verify failed"), FATAL, "classification of a TLS failure")


# -- backoff ------------------------------------------------------------

def first_retry_ceiling_is_the_base_delay():
    p = policy(frac=1.0, base=2.0)
    eq(p.next_delay(0, 500), 2.0, "delay on attempt 0 with full jitter")


def backoff_doubles():
    p = policy(frac=1.0, base=2.0)
    eq(p.next_delay(1, 500), 4.0, "delay on attempt 1")
    eq(p.next_delay(2, 500), 8.0, "delay on attempt 2")


def jitter_is_applied_within_the_ceiling():
    p = policy(frac=0.25, base=4.0)
    eq(p.next_delay(1, 500), 2.0, "quarter jitter of an 8s ceiling")


def the_ceiling_is_capped_before_jitter():
    # Ceiling would be 1 * 2**6 = 64, capped to 10, then jittered by half -> 5.
    # Jittering first and capping after would give min(32, 10) = 10.
    # attempts=10 so the attempt limit is not what is being tested here.
    p = policy(frac=0.5, base=1.0, cap=10.0, attempts=10)
    eq(p.next_delay(6, 500), 5.0, "half jitter of a ceiling capped at 10")


# -- throttling ---------------------------------------------------------

def throttled_waits_exactly_retry_after():
    p = policy(frac=0.5, base=1.0)
    eq(p.next_delay(0, 429, retry_after=7.5), 7.5, "delay for a throttled request")


def throttled_ignores_jitter_entirely():
    p = policy(frac=0.1, base=1.0)
    eq(p.next_delay(3, 429, retry_after=2.0), 2.0, "delay for a throttled request")


def throttled_is_capped_at_max_delay():
    p = policy(frac=0.5, base=1.0, cap=10.0)
    eq(p.next_delay(0, 429, retry_after=100.0), 10.0, "capped delay for a throttled request")


def throttled_without_retry_after_falls_back_to_backoff():
    p = policy(frac=1.0, base=3.0)
    eq(p.next_delay(0, 429), 3.0, "delay for a throttled request with no retry_after")


# -- limits -------------------------------------------------------------

def fatal_never_retries():
    p = policy()
    eq(p.next_delay(0, 404), None, "delay after a fatal error")


def the_last_permitted_attempt_gets_no_delay():
    p = policy(frac=0.5, base=1.0, attempts=3)
    if p.next_delay(1, 500) is None:
        raise AssertionError("attempt 1 of 3 should still produce a delay")
    eq(p.next_delay(2, 500), None, "delay on the last of 3 attempts")


def one_attempt_means_no_retry():
    p = policy(attempts=1)
    eq(p.next_delay(0, 500), None, "delay when only one try is permitted")


def elapsed_budget_counts_the_pending_delay():
    # 8 already spent, a 4s delay would reach 12, over the 10s budget.
    p = policy(frac=1.0, base=4.0, elapsed_budget=10.0)
    eq(p.next_delay(0, 500, elapsed=8.0), None, "delay that would overrun the budget")


def landing_exactly_on_the_budget_is_allowed():
    p = policy(frac=1.0, base=4.0, elapsed_budget=10.0)
    eq(p.next_delay(0, 500, elapsed=6.0), 4.0, "delay that lands exactly on the budget")


def the_budget_applies_to_throttling_too():
    p = policy(frac=0.5, base=1.0, elapsed_budget=10.0)
    eq(p.next_delay(0, 429, retry_after=9.0, elapsed=5.0), None,
       "throttled delay that would overrun the budget")


CHECKS = [
    ("server_errors_are_retryable", server_errors_are_retryable),
    ("too_many_requests_is_throttled", too_many_requests_is_throttled),
    ("other_client_errors_are_fatal", other_client_errors_are_fatal),
    ("success_is_fatal", success_is_fatal),
    ("network_timeout_is_retryable", network_timeout_is_retryable),
    ("network_reset_is_retryable", network_reset_is_retryable),
    ("network_hints_are_case_insensitive", network_hints_are_case_insensitive),
    ("other_network_errors_are_fatal", other_network_errors_are_fatal),
    ("first_retry_ceiling_is_the_base_delay", first_retry_ceiling_is_the_base_delay),
    ("backoff_doubles", backoff_doubles),
    ("jitter_is_applied_within_the_ceiling", jitter_is_applied_within_the_ceiling),
    ("the_ceiling_is_capped_before_jitter", the_ceiling_is_capped_before_jitter),
    ("throttled_waits_exactly_retry_after", throttled_waits_exactly_retry_after),
    ("throttled_ignores_jitter_entirely", throttled_ignores_jitter_entirely),
    ("throttled_is_capped_at_max_delay", throttled_is_capped_at_max_delay),
    ("throttled_without_retry_after_falls_back_to_backoff",
     throttled_without_retry_after_falls_back_to_backoff),
    ("fatal_never_retries", fatal_never_retries),
    ("the_last_permitted_attempt_gets_no_delay", the_last_permitted_attempt_gets_no_delay),
    ("one_attempt_means_no_retry", one_attempt_means_no_retry),
    ("elapsed_budget_counts_the_pending_delay", elapsed_budget_counts_the_pending_delay),
    ("landing_exactly_on_the_budget_is_allowed", landing_exactly_on_the_budget_is_allowed),
    ("the_budget_applies_to_throttling_too", the_budget_applies_to_throttling_too),
]

for name, fn in CHECKS:
    check(name, fn)

for f in FAILURES:
    print("FAIL: " + f)
print(f"RESULT {PASSED} passed {len(FAILURES)} failed")
sys.exit(1 if FAILURES else 0)
