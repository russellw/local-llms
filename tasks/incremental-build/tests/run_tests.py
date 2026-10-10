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


# -- a chain of two ------------------------------------------------------

def first_build_of_a_chain():
    eq(build(chain(), {"s": b"x"}, Store()).ran, ["a", "b"], "ran")


def output_of_a_chain():
    store = Store()
    build(chain(), {"s": b"x"}, store)
    eq(store.output("b"), b"<X>", "output of b")


def second_build_with_nothing_changed():
    g, store = chain(), Store()
    build(g, {"s": b"x"}, store)
    r = build(g, {"s": b"x"}, store)
    eq(r.ran, [], "ran")
    eq(r.up_to_date, ["a", "b"], "up to date")


def build_after_editing_the_source():
    g, store = chain(), Store()
    build(g, {"s": b"x"}, store)
    eq(build(g, {"s": b"y"}, store).ran, ["a", "b"], "ran")


def build_after_editing_and_building():
    g, store = chain(), Store()
    build(g, {"s": b"x"}, store)
    build(g, {"s": b"y"}, store)
    r = build(g, {"s": b"y"}, store)
    eq(r.ran, [], "ran")
    eq(store.output("b"), b"<Y>", "output of b")


def two_chains_one_source_edited():
    g = Graph()
    g.add("a", deps=["s"], recipe=upper("s"))
    g.add("b", deps=["t"], recipe=upper("t"))
    store = Store()
    build(g, {"s": b"x", "t": b"y"}, store)
    eq(build(g, {"s": b"x", "t": b"z"}, store).ran, ["b"], "ran")


def recipe_with_two_inputs():
    g = Graph()
    g.add("a", deps=["s"], recipe=upper("s"))
    g.add("b", deps=["a", "t"], recipe=join("a", "t"))
    store = Store()
    build(g, {"s": b"x", "t": b"y"}, store)
    eq(store.output("b"), b"X+y", "output of b")


def version_2_of_the_first_recipe():
    store = Store()
    build(chain(), {"s": b"x"}, store)
    g = Graph()
    g.add("a", deps=["s"], recipe=upper("s"), version=2)
    g.add("b", deps=["a"], recipe=wrap("a"))
    r = build(g, {"s": b"x"}, store)
    if "a" not in r.ran:
        raise AssertionError(f"ran was {r.ran!r}, expected it to include 'a'")


# -- a goal --------------------------------------------------------------

def goal_at_the_end_of_three():
    g = Graph()
    g.add("a", deps=["s"], recipe=upper("s"))
    g.add("b", deps=["a"], recipe=wrap("a"))
    g.add("c", deps=["b"], recipe=wrap("b"))
    store = Store()
    eq(build(g, {"s": b"x"}, store, goal="c").ran, ["a", "b", "c"], "ran")
    eq(store.output("c"), b"<<X>>", "output of c")


def goal_beside_another_target():
    g = chain()
    g.add("c", deps=["s"], recipe=wrap("s"))
    store = Store()
    eq(build(g, {"s": b"x"}, store, goal="b").ran, ["a", "b"], "ran")
    eq(store.output("c"), None, "output of c")


# -- a recipe that raises ------------------------------------------------

def first_of_three_raises():
    g = Graph()
    g.add("a", deps=["s"], recipe=fails)
    g.add("b", deps=["a"], recipe=wrap("a"))
    g.add("c", deps=["b"], recipe=wrap("b"))
    r = build(g, {"s": b"x"}, Store())
    eq(r.failed, ["a"], "failed")
    eq(r.ran, [], "ran")
    eq(r.blocked, ["b", "c"], "blocked")


# -- graphs that cannot be built ----------------------------------------

def dependency_on_nope():
    g = Graph()
    g.add("a", deps=["nope"], recipe=upper("nope"))
    raises_build_error(lambda: build(g, {"s": b"x"}, Store()), "build")


def a_and_b_need_each_other():
    g = Graph()
    g.add("a", deps=["b"], recipe=wrap("b"))
    g.add("b", deps=["a"], recipe=wrap("a"))
    raises_build_error(lambda: build(g, {}, Store()), "build")


CHECKS = [
    ("first_build_of_a_chain", first_build_of_a_chain),
    ("output_of_a_chain", output_of_a_chain),
    ("second_build_with_nothing_changed", second_build_with_nothing_changed),
    ("build_after_editing_the_source", build_after_editing_the_source),
    ("build_after_editing_and_building", build_after_editing_and_building),
    ("two_chains_one_source_edited", two_chains_one_source_edited),
    ("recipe_with_two_inputs", recipe_with_two_inputs),
    ("version_2_of_the_first_recipe", version_2_of_the_first_recipe),
    ("goal_at_the_end_of_three", goal_at_the_end_of_three),
    ("goal_beside_another_target", goal_beside_another_target),
    ("first_of_three_raises", first_of_three_raises),
    ("dependency_on_nope", dependency_on_nope),
    ("a_and_b_need_each_other", a_and_b_need_each_other),
]

for name, fn in CHECKS:
    check(name, fn)

for f in FAILURES:
    print("FAIL: " + f)
print(f"RESULT {PASSED} passed {len(FAILURES)} failed")
sys.exit(1 if FAILURES else 0)
