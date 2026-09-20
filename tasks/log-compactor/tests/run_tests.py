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

def min_count_one_keeps_a_single_record():
    eq(compact([(1, "a", "x")], 1), [("a", "x")], "output for one record")


def min_count_is_at_least_not_more_than():
    recs = [(1, "a", "x"), (2, "a", "y"), (3, "b", "z")]
    eq(compact(recs, 2), [("a", "y")], "output with min_count=2")


def a_key_below_the_threshold_is_dropped():
    recs = [(1, "a", "x"), (2, "b", "y"), (3, "b", "z")]
    eq(compact(recs, 2), [("b", "z")], "output with min_count=2")


# -- highest timestamp wins, not last seen -----------------------------

def out_of_order_records_pick_the_highest_timestamp():
    recs = [(5, "a", "late"), (1, "a", "early")]
    eq(compact(recs, 1), [("a", "late")], "value for a key with a stale follow-up")


def a_tie_on_timestamp_goes_to_the_later_record():
    recs = [(5, "a", "first"), (5, "a", "second")]
    eq(compact(recs, 1), [("a", "second")], "value when two records tie on timestamp")


# -- first-appearance ordering -----------------------------------------

def output_follows_first_appearance_not_the_alphabet():
    recs = [(1, "z", "1"), (2, "a", "2"), (3, "m", "3")]
    eq(compact(recs, 1), [("z", "1"), ("a", "2"), ("m", "3")],
       "output order")


def first_appearance_survives_later_updates():
    recs = [(1, "z", "1"), (2, "a", "2"), (9, "z", "updated")]
    eq(compact(recs, 1), [("z", "updated"), ("a", "2")], "output order")


def ordering_holds_when_some_keys_are_dropped():
    recs = [(1, "z", "1"), (2, "a", "2"), (3, "a", "3"), (4, "z", "4")]
    eq(compact(recs, 2), [("z", "4"), ("a", "3")], "output order with a threshold")


# -- the stream is walked once -----------------------------------------

def accepts_a_generator():
    def gen():
        yield (1, "a", "x")
        yield (2, "b", "y")
    eq(compact(gen(), 1), [("a", "x"), ("b", "y")], "output from a generator")


def empty_stream():
    eq(compact(iter([]), 1), [], "output for an empty stream")


# -- cost ---------------------------------------------------------------

def stays_linear_in_the_number_of_records():
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
            f"compacting {n} records took {elapsed:.1f}s, which is too slow: "
            "per-record work is growing with the number of distinct keys seen "
            "so far. See the cost section of the spec."
        )


def stays_linear_when_keys_repeat():
    n = 40000
    recs = [(i, f"key-{i % 20000}", i) for i in range(n)]
    t0 = time.monotonic()
    out = compact(recs, 2)
    elapsed = time.monotonic() - t0
    if len(out) != 20000:
        raise AssertionError(f"expected 20000 rows, got {len(out)}")
    if elapsed > 3.0:
        raise AssertionError(
            f"compacting {n} records took {elapsed:.1f}s, which is too slow: "
            "per-record work is growing with the number of distinct keys seen "
            "so far. See the cost section of the spec."
        )


CHECKS = [
    ("min_count_one_keeps_a_single_record", min_count_one_keeps_a_single_record),
    ("min_count_is_at_least_not_more_than", min_count_is_at_least_not_more_than),
    ("a_key_below_the_threshold_is_dropped", a_key_below_the_threshold_is_dropped),
    ("out_of_order_records_pick_the_highest_timestamp",
     out_of_order_records_pick_the_highest_timestamp),
    ("a_tie_on_timestamp_goes_to_the_later_record", a_tie_on_timestamp_goes_to_the_later_record),
    ("output_follows_first_appearance_not_the_alphabet",
     output_follows_first_appearance_not_the_alphabet),
    ("first_appearance_survives_later_updates", first_appearance_survives_later_updates),
    ("ordering_holds_when_some_keys_are_dropped", ordering_holds_when_some_keys_are_dropped),
    ("accepts_a_generator", accepts_a_generator),
    ("empty_stream", empty_stream),
    ("stays_linear_in_the_number_of_records", stays_linear_in_the_number_of_records),
    ("stays_linear_when_keys_repeat", stays_linear_when_keys_repeat),
]

for name, fn in CHECKS:
    check(name, fn)

for f in FAILURES:
    print("FAIL: " + f)
print(f"RESULT {PASSED} passed {len(FAILURES)} failed")
sys.exit(1 if FAILURES else 0)
