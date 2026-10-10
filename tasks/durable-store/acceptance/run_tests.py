"""Hidden test suite. Curated one-line failures only; never a traceback."""

import sys

from src.fs import FakeFS, PowerLoss
from src.store import Store

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


def contents(fs):
    store = Store.open(fs)
    return {key: store.get(key) for key in store.keys()}


def store_with(*commits):
    fs = FakeFS()
    store = Store.open(fs)
    for changes in commits:
        store.commit(changes)
    return fs


def _show(state):
    return "{" + ", ".join(f"{k}={v}" for k, v in sorted(state.items())) + "}"


def power_lost_at_every_point(before, changes, after):
    """Cut the power at each change of a commit, under every outcome the
    filesystem allows, and open what is left. Then let the commit finish and
    cut the power after it returned."""
    n = 0
    while True:
        fs = store_with(*before)
        fs.fail_after(n)
        try:
            Store.open(fs).commit(changes)
            returned = True
        except PowerLoss:
            returned = False
        allowed = [after] if returned else [contents(store_with(*before)), after]
        for i, left in enumerate(fs.power_loss_outcomes()):
            try:
                got = contents(left)
            except Exception as e:
                when = "after the commit returned" if returned else f"at change {n}"
                raise AssertionError(
                    f"opening after a power loss {when} (outcome {i}) raised {type(e).__name__}")
            if got not in allowed:
                when = "after the commit returned" if returned else f"at change {n}"
                raise AssertionError(
                    f"after a power loss {when} (outcome {i}) the store held {_show(got)}, "
                    f"expected " + " or ".join(_show(a) for a in allowed))
        if returned:
            return
        n += 1
        if n > 500:
            raise AssertionError("the commit never returned")


def two_keys_both_changed():
    power_lost_at_every_point(
        [{"a": "1", "b": "1"}], {"a": "2", "b": "2"}, {"a": "2", "b": "2"})


def first_commit_of_two_keys():
    power_lost_at_every_point([], {"a": "1", "b": "1"}, {"a": "1", "b": "1"})


def one_key_set_and_one_deleted():
    power_lost_at_every_point(
        [{"a": "1", "b": "1"}], {"a": "2", "b": None}, {"a": "2"})


def third_commit_after_two():
    power_lost_at_every_point(
        [{"a": "1", "b": "1"}, {"b": "2", "c": "2"}], {"a": "3", "c": None},
        {"a": "3", "b": "2"})


def a_commit_after_a_lost_one():
    # The power goes out partway through a commit, then the store is opened
    # and committed to again. Whatever the first one left lying around, the
    # second must behave like any other commit.
    for n in range(12):
        fs = store_with({"a": "1", "b": "1"})
        fs.fail_after(n)
        try:
            Store.open(fs).commit({"a": "2", "b": "2"})
            break
        except PowerLoss:
            pass
        for i, left in enumerate(fs.power_loss_outcomes()):
            start = contents(left)
            store = Store.open(left)
            store.commit({"b": "3"})
            want = dict(start, b="3")
            for j, again in enumerate(left.power_loss_outcomes()):
                got = contents(again)
                if got != want:
                    raise AssertionError(
                        f"after a power loss at change {n} (outcome {i}), a commit, and a "
                        f"second power loss (outcome {j}), the store held {_show(got)}, "
                        f"expected {_show(want)}")


def one_key_changed_among_fifty():
    fs = store_with({f"k{i:02}": "x" * 1000 for i in range(50)})
    store = Store.open(fs)
    before = fs.bytes_written
    store.commit({"k07": "y" * 1000})
    written = fs.bytes_written - before
    if written > 10000:
        raise AssertionError(f"bytes written by the commit was {written}, expected at most 10000")


CHECKS = [
    ("two_keys_both_changed", two_keys_both_changed),
    ("first_commit_of_two_keys", first_commit_of_two_keys),
    ("one_key_set_and_one_deleted", one_key_set_and_one_deleted),
    ("third_commit_after_two", third_commit_after_two),
    ("a_commit_after_a_lost_one", a_commit_after_a_lost_one),
    ("one_key_changed_among_fifty", one_key_changed_among_fifty),
]

for name, fn in CHECKS:
    check(name, fn)

for f in FAILURES:
    print("FAIL: " + f)
print(f"RESULT {PASSED} passed {len(FAILURES)} failed")
sys.exit(1 if FAILURES else 0)
