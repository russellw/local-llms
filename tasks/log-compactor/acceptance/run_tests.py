"""Hidden test suite. Curated one-line failures only; never a traceback."""

import random
import sys
import time

from src.compactor import compact

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


# -- the threshold is inclusive ----------------------------------------

def one_record_min_count_1():
    eq(compact([(1, "a", "x")], 1), [("a", "x")], "output for one record")


def three_records_min_count_2():
    recs = [(1, "a", "x"), (2, "a", "y"), (3, "b", "z")]
    eq(compact(recs, 2), [("a", "y")], "output with min_count=2")


def mixed_counts_min_count_2():
    recs = [(1, "a", "x"), (2, "b", "y"), (3, "b", "z")]
    eq(compact(recs, 2), [("b", "z")], "output with min_count=2")


# -- highest timestamp wins, not last seen -----------------------------

def out_of_order_timestamps():
    recs = [(5, "a", "late"), (1, "a", "early")]
    eq(compact(recs, 1), [("a", "late")], "value for 'a'")


def equal_timestamps():
    recs = [(5, "a", "first"), (5, "a", "second")]
    eq(compact(recs, 1), [("a", "second")], "value for 'a'")


# -- first-appearance ordering -----------------------------------------

def three_keys_not_in_alphabetical_order():
    recs = [(1, "z", "1"), (2, "a", "2"), (3, "m", "3")]
    eq(compact(recs, 1), [("z", "1"), ("a", "2"), ("m", "3")],
       "output order")


def a_key_updated_after_a_later_key_appears():
    recs = [(1, "z", "1"), (2, "a", "2"), (9, "z", "updated")]
    eq(compact(recs, 1), [("z", "updated"), ("a", "2")], "output order")


def ordering_with_a_threshold():
    recs = [(1, "z", "1"), (2, "a", "2"), (3, "a", "3"), (4, "z", "4")]
    eq(compact(recs, 2), [("z", "4"), ("a", "3")], "output order with a threshold")


# -- the stream is walked once -----------------------------------------

def generator_input():
    def gen():
        yield (1, "a", "x")
        yield (2, "b", "y")
    eq(compact(gen(), 1), [("a", "x"), ("b", "y")], "output")


def empty_input():
    eq(compact(iter([]), 1), [], "output")


# -- cost ---------------------------------------------------------------

def forty_thousand_distinct_keys():
    # Sized so the two shapes are ~500x apart on this class of machine: a dict
    # lookup per record finishes in hundredths of a second, a scan of the keys
    # seen so far takes the better part of ten. Anything in between is not a
    # thing a correct implementation does.
    n = 40000
    rnd = random.Random(7)
    recs = [(rnd.randrange(1 << 30), f"key-{i}", i) for i in range(n)]
    t0 = time.monotonic()
    out = compact(recs, 1)
    elapsed = time.monotonic() - t0
    if len(out) != n:
        raise AssertionError(f"compacting {n} distinct keys returned {len(out)} rows")
    if elapsed > 3.0:
        raise AssertionError(
            f"compacting {n} records took {elapsed:.1f}s; the limit is 3.0s"
        )


def forty_thousand_records_over_twenty_thousand_keys():
    n = 40000
    recs = [(i, f"key-{i % 20000}", i) for i in range(n)]
    t0 = time.monotonic()
    out = compact(recs, 2)
    elapsed = time.monotonic() - t0
    if len(out) != 20000:
        raise AssertionError(f"expected 20000 rows, got {len(out)}")
    if elapsed > 3.0:
        raise AssertionError(
            f"compacting {n} records took {elapsed:.1f}s; the limit is 3.0s"
        )


CHECKS = [
    ("equal_timestamps", equal_timestamps),
    ("three_keys_not_in_alphabetical_order",
     three_keys_not_in_alphabetical_order),
    ("a_key_updated_after_a_later_key_appears", a_key_updated_after_a_later_key_appears),
    ("ordering_with_a_threshold", ordering_with_a_threshold),
    ("forty_thousand_distinct_keys", forty_thousand_distinct_keys),
    ("forty_thousand_records_over_twenty_thousand_keys", forty_thousand_records_over_twenty_thousand_keys),
]

for name, fn in CHECKS:
    check(name, fn)

for f in FAILURES:
    print("FAIL: " + f)
print(f"RESULT {PASSED} passed {len(FAILURES)} failed")
sys.exit(1 if FAILURES else 0)
