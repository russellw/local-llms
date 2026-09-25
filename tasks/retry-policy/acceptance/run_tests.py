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

def classification_of_408_and_5xx():
    for s in (408, 500, 502, 503, 504):
        eq(classify(s), RETRYABLE, f"classification of {s}")


def classification_of_429():
    eq(classify(429), THROTTLED, "classification of 429")


def classification_of_other_4xx():
    for s in (400, 401, 403, 404, 422):
        eq(classify(s), FATAL, f"classification of {s}")


def classification_of_200():
    eq(classify(200), FATAL, "classification of 200")


def classification_of_a_timeout_message():
    eq(classify(None, "connection timeout"), RETRYABLE, "classification of a timeout")


def classification_of_a_reset_message():
    eq(classify(None, "Connection reset by peer"), RETRYABLE, "classification of a reset")


def classification_of_an_upper_case_message():
    eq(classify(None, "TIMEOUT while reading"), RETRYABLE, "classification of an upper-case timeout")


def classification_of_a_tls_message():
    eq(classify(None, "certificate verify failed"), FATAL, "classification of a TLS failure")


# -- backoff ------------------------------------------------------------

def delay_on_attempt_0():
    p = policy(frac=1.0, base=2.0)
    eq(p.next_delay(0, 500), 2.0, "delay on attempt 0")


def delay_on_attempts_1_and_2():
    p = policy(frac=1.0, base=2.0)
    eq(p.next_delay(1, 500), 4.0, "delay on attempt 1")
    eq(p.next_delay(2, 500), 8.0, "delay on attempt 2")


def delay_with_a_quarter_jitter():
    p = policy(frac=0.25, base=4.0)
    eq(p.next_delay(1, 500), 2.0, "delay on attempt 1")


def delay_on_attempt_6_with_a_cap_of_10():
    # Ceiling would be 1 * 2**6 = 64, capped to 10, then jittered by half -> 5.
    # Jittering first and capping after would give min(32, 10) = 10.
    # attempts=10 so the attempt limit is not what is being tested here.
    p = policy(frac=0.5, base=1.0, cap=10.0, attempts=10)
    eq(p.next_delay(6, 500), 5.0, "delay on attempt 6")


# -- throttling ---------------------------------------------------------

def delay_for_429_with_retry_after():
    p = policy(frac=0.5, base=1.0)
    eq(p.next_delay(0, 429, retry_after=7.5), 7.5, "delay for status 429")


def delay_for_429_on_attempt_3():
    p = policy(frac=0.1, base=1.0)
    eq(p.next_delay(3, 429, retry_after=2.0), 2.0, "delay for status 429")


def delay_for_429_with_a_large_retry_after():
    p = policy(frac=0.5, base=1.0, cap=10.0)
    eq(p.next_delay(0, 429, retry_after=100.0), 10.0, "delay for status 429")


def delay_for_429_without_retry_after():
    p = policy(frac=1.0, base=3.0)
    eq(p.next_delay(0, 429), 3.0, "delay for status 429")


# -- limits -------------------------------------------------------------

def delay_for_404():
    p = policy()
    eq(p.next_delay(0, 404), None, "delay for status 404")


def delay_on_attempts_1_and_2_of_3():
    p = policy(frac=0.5, base=1.0, attempts=3)
    if p.next_delay(1, 500) is None:
        raise AssertionError("attempt 1 of 3 returned no delay")
    eq(p.next_delay(2, 500), None, "delay on the last of 3 attempts")


def delay_when_max_attempts_is_1():
    p = policy(attempts=1)
    eq(p.next_delay(0, 500), None, "delay when only one try is permitted")


def delay_with_8_of_10_seconds_spent():
    # 8 already spent, a 4s delay would reach 12, over the 10s budget.
    p = policy(frac=1.0, base=4.0, elapsed_budget=10.0)
    eq(p.next_delay(0, 500, elapsed=8.0), None, "delay with elapsed=8.0")


def delay_with_6_of_10_seconds_spent():
    p = policy(frac=1.0, base=4.0, elapsed_budget=10.0)
    eq(p.next_delay(0, 500, elapsed=6.0), 4.0, "delay with elapsed=6.0")


def delay_for_429_with_5_of_10_seconds_spent():
    p = policy(frac=0.5, base=1.0, elapsed_budget=10.0)
    eq(p.next_delay(0, 429, retry_after=9.0, elapsed=5.0), None,
       "delay for status 429 with elapsed=5.0")


CHECKS = [
    ("classification_of_429", classification_of_429),
    ("delay_on_attempt_6_with_a_cap_of_10", delay_on_attempt_6_with_a_cap_of_10),
    ("delay_for_429_with_retry_after", delay_for_429_with_retry_after),
    ("delay_for_429_on_attempt_3", delay_for_429_on_attempt_3),
    ("delay_for_429_with_a_large_retry_after", delay_for_429_with_a_large_retry_after),
    ("delay_for_429_without_retry_after",
     delay_for_429_without_retry_after),
    ("delay_with_8_of_10_seconds_spent", delay_with_8_of_10_seconds_spent),
    ("delay_with_6_of_10_seconds_spent", delay_with_6_of_10_seconds_spent),
    ("delay_for_429_with_5_of_10_seconds_spent", delay_for_429_with_5_of_10_seconds_spent),
]

for name, fn in CHECKS:
    check(name, fn)

for f in FAILURES:
    print("FAIL: " + f)
print(f"RESULT {PASSED} passed {len(FAILURES)} failed")
sys.exit(1 if FAILURES else 0)
