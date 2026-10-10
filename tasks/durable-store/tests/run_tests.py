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


def one_key():
    store = Store.open(FakeFS())
    store.commit({"colour": "blue"})
    eq(store.get("colour"), "blue", "get('colour')")


def one_key_reopened():
    eq(contents(store_with({"colour": "blue"})), {"colour": "blue"}, "contents")


def key_never_set():
    store = Store.open(store_with({"colour": "blue"}))
    eq(store.get("size"), None, "get('size')")


def empty_filesystem():
    eq(contents(FakeFS()), {}, "contents")


def three_keys_sorted():
    fs = store_with({"pear": "1", "apple": "2", "fig": "3"})
    eq(Store.open(fs).keys(), ["apple", "fig", "pear"], "keys()")


def same_key_twice():
    eq(contents(store_with({"colour": "blue"}, {"colour": "red"})),
       {"colour": "red"}, "contents")


def set_then_delete_reopened():
    fs = store_with({"colour": "blue", "size": "large"}, {"size": None})
    eq(contents(fs), {"colour": "blue"}, "contents")


def delete_of_a_key_never_set():
    fs = store_with({"colour": "blue"}, {"size": None})
    eq(contents(fs), {"colour": "blue"}, "contents")


def key_with_a_slash():
    eq(contents(store_with({"a/b": "1"})), {"a/b": "1"}, "contents")


def non_ascii_value():
    eq(contents(store_with({"name": "Zoë"})), {"name": "Zoë"}, "contents")


def power_lost_after_commit_returned():
    fs = store_with({"colour": "blue"})
    eq(contents(fs.after_power_loss()), {"colour": "blue"}, "contents after the power came back")


CHECKS = [
    ("one_key", one_key),
    ("one_key_reopened", one_key_reopened),
    ("key_never_set", key_never_set),
    ("empty_filesystem", empty_filesystem),
    ("three_keys_sorted", three_keys_sorted),
    ("same_key_twice", same_key_twice),
    ("set_then_delete_reopened", set_then_delete_reopened),
    ("delete_of_a_key_never_set", delete_of_a_key_never_set),
    ("key_with_a_slash", key_with_a_slash),
    ("non_ascii_value", non_ascii_value),
    ("power_lost_after_commit_returned", power_lost_after_commit_returned),
]

for name, fn in CHECKS:
    check(name, fn)

for f in FAILURES:
    print("FAIL: " + f)
print(f"RESULT {PASSED} passed {len(FAILURES)} failed")
sys.exit(1 if FAILURES else 0)
