"""Hidden test suite. Curated one-line failures only; never a traceback."""

import sys

from src.graph import BuildError, Graph
from src.store import Store
from src.build import build

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


def raises_build_error(fn, what):
    try:
        fn()
    except BuildError:
        return
    except Exception as e:
        raise AssertionError(f"{what} raised {type(e).__name__}, expected BuildError")
    raise AssertionError(f"{what} returned normally, expected BuildError")


def upper(name):
    return lambda i: i[name].upper()


def wrap(name):
    return lambda i: b"<" + i[name] + b">"


def join(*names):
    return lambda i: b"+".join(i[n] for n in names)


def fails(i):
    raise ValueError("recipe failed")


class Counter:
    """A recipe that counts its calls."""

    def __init__(self, fn):
        self.fn = fn
        self.calls = 0

    def __call__(self, i):
        self.calls += 1
        return self.fn(i)


def chain():
    g = Graph()
    g.add("a", deps=["s"], recipe=upper("s"))
    g.add("b", deps=["a"], recipe=wrap("a"))
    return g


# -- order ---------------------------------------------------------------

def a_needs_c_then_b_then_c():
    g = Graph()
    g.add("a", deps=["c"], recipe=wrap("c"))
    g.add("b", deps=["s"], recipe=upper("s"))
    g.add("c", deps=["s"], recipe=upper("s"))
    eq(build(g, {"s": b"x"}, Store()).ran, ["b", "c", "a"], "ran")


def zlib_then_app():
    g = Graph()
    g.add("zlib", deps=["s"], recipe=upper("s"))
    g.add("app", deps=["t"], recipe=upper("t"))
    eq(build(g, {"s": b"x", "t": b"y"}, Store()).ran, ["zlib", "app"], "ran")


# -- an input that comes out the same -------------------------------------

def trailing_space_added_to_the_source():
    g = Graph()
    g.add("norm", deps=["s"], recipe=lambda i: i["s"].strip())
    g.add("out", deps=["norm"], recipe=wrap("norm"))
    store = Store()
    build(g, {"s": b"x"}, store)
    r = build(g, {"s": b"x  "}, store)
    eq(r.ran, ["norm"], "ran")
    eq(r.up_to_date, ["out"], "up to date")


def dependencies_listed_the_other_way_round():
    store = Store()
    g = Graph()
    g.add("c", deps=["s", "t"], recipe=join("s", "t"))
    build(g, {"s": b"x", "t": b"y"}, store)
    g = Graph()
    g.add("c", deps=["t", "s"], recipe=join("s", "t"))
    eq(build(g, {"s": b"x", "t": b"y"}, store).ran, [], "ran")


# -- a recipe that raises ------------------------------------------------

def first_of_three_raises_and_the_third_is_separate():
    g = Graph()
    g.add("a", deps=["s"], recipe=fails)
    g.add("b", deps=["a"], recipe=wrap("a"))
    g.add("d", deps=["s"], recipe=upper("s"))
    r = build(g, {"s": b"x"}, Store())
    eq(r.failed, ["a"], "failed")
    eq(r.blocked, ["b"], "blocked")
    eq(r.ran, ["d"], "ran")


# -- graphs that cannot be built ----------------------------------------

def dependency_on_nope_declared_second():
    first = Counter(upper("s"))
    g = Graph()
    g.add("a", deps=["s"], recipe=first)
    g.add("b", deps=["nope"], recipe=upper("nope"))
    raises_build_error(lambda: build(g, {"s": b"x"}, Store()), "build")
    eq(first.calls, 0, "calls to a's recipe")


def a_and_b_need_each_other_after_c():
    first = Counter(upper("s"))
    g = Graph()
    g.add("c", deps=["s"], recipe=first)
    g.add("a", deps=["b"], recipe=wrap("b"))
    g.add("b", deps=["a"], recipe=wrap("a"))
    raises_build_error(lambda: build(g, {"s": b"x"}, Store()), "build")
    eq(first.calls, 0, "calls to c's recipe")


CHECKS = [
    ("a_needs_c_then_b_then_c", a_needs_c_then_b_then_c),
    ("zlib_then_app", zlib_then_app),
    ("trailing_space_added_to_the_source", trailing_space_added_to_the_source),
    ("dependencies_listed_the_other_way_round", dependencies_listed_the_other_way_round),
    ("first_of_three_raises_and_the_third_is_separate", first_of_three_raises_and_the_third_is_separate),
    ("dependency_on_nope_declared_second", dependency_on_nope_declared_second),
    ("a_and_b_need_each_other_after_c", a_and_b_need_each_other_after_c),
]

for name, fn in CHECKS:
    check(name, fn)

for f in FAILURES:
    print("FAIL: " + f)
print(f"RESULT {PASSED} passed {len(FAILURES)} failed")
sys.exit(1 if FAILURES else 0)
