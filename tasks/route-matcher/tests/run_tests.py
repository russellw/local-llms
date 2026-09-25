"""Hidden test suite. Curated one-line failures only; never a traceback."""

import sys

from src.router import Router

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


def build(*pairs):
    r = Router()
    for pattern, handler in pairs:
        r.add(pattern, handler)
    return r


# -- specificity beats registration order ------------------------------

def me_route_registered_second():
    r = build(("/users/:id", "param"), ("/users/me", "static"))
    eq(r.match("/users/me")[0], "static", "handler for /users/me")


def me_route_registered_first():
    r = build(("/users/me", "static"), ("/users/:id", "param"))
    eq(r.match("/users/me")[0], "static", "handler for /users/me")


def other_path_with_both_registered():
    r = build(("/users/:id", "param"), ("/users/me", "static"))
    eq(r.match("/users/42"), ("param", {"id": "42"}), "match for /users/42")


def wildcard_and_param_both_registered():
    r = build(("/*rest", "wild"), ("/users/:id", "param"))
    eq(r.match("/users/42")[0], "param", "handler for /users/42")


def patterns_differing_at_the_first_segment():
    r = build(("/:a/:b/c", "params"), ("/x/:b/c", "static_first"))
    eq(r.match("/x/y/c")[0], "static_first", "handler for /x/y/c")


def two_patterns_of_the_same_shape():
    r = build(("/:a/b", "first"), ("/:c/b", "second"))
    eq(r.match("/z/b")[0], "first", "handler for /z/b")


# -- captures ----------------------------------------------------------

def captures_for_one_parameter():
    r = build(("/users/:id", "h"),)
    eq(r.match("/users/7")[1], {"id": "7"}, "captured params")


def captures_for_two_parameters():
    r = build(("/:org/repos/:name", "h"),)
    eq(r.match("/acme/repos/tools")[1], {"org": "acme", "name": "tools"},
       "captured params")


def wildcard_over_three_segments():
    r = build(("/files/*path", "h"),)
    eq(r.match("/files/a/b/c.txt")[1], {"path": "a/b/c.txt"}, "captured wildcard")


def wildcard_over_one_segment():
    r = build(("/files/*path", "h"),)
    eq(r.match("/files/a.txt")[1], {"path": "a.txt"}, "captured wildcard")


def wildcard_over_no_segments():
    r = build(("/files/*path", "h"),)
    eq(r.match("/files")[1], {"path": ""}, "captured wildcard")


# -- trailing slashes and the root -------------------------------------

def path_with_a_trailing_slash():
    r = build(("/users/me", "h"),)
    eq(r.match("/users/me/")[0], "h", "handler for /users/me/")


def root_path():
    r = build(("/", "root"),)
    eq(r.match("/")[0], "root", "handler for /")


def root_against_a_one_segment_pattern():
    r = build(("/:id", "param"),)
    eq(r.match("/"), None, "match for /")


# -- no match ----------------------------------------------------------

def unregistered_path():
    r = build(("/users/:id", "h"),)
    eq(r.match("/orders/1"), None, "match for /orders/1")


def path_deeper_than_the_pattern():
    r = build(("/users/:id", "h"),)
    eq(r.match("/users/1/edit"), None, "match for /users/1/edit")


CHECKS = [
    ("me_route_registered_second", me_route_registered_second),
    ("me_route_registered_first", me_route_registered_first),
    ("other_path_with_both_registered", other_path_with_both_registered),
    ("wildcard_and_param_both_registered", wildcard_and_param_both_registered),
    ("patterns_differing_at_the_first_segment",
     patterns_differing_at_the_first_segment),
    ("two_patterns_of_the_same_shape",
     two_patterns_of_the_same_shape),
    ("captures_for_one_parameter", captures_for_one_parameter),
    ("captures_for_two_parameters", captures_for_two_parameters),
    ("wildcard_over_three_segments", wildcard_over_three_segments),
    ("wildcard_over_one_segment", wildcard_over_one_segment),
    ("wildcard_over_no_segments", wildcard_over_no_segments),
    ("path_with_a_trailing_slash", path_with_a_trailing_slash),
    ("root_path", root_path),
    ("root_against_a_one_segment_pattern", root_against_a_one_segment_pattern),
    ("unregistered_path", unregistered_path),
    ("path_deeper_than_the_pattern", path_deeper_than_the_pattern),
]

for name, fn in CHECKS:
    check(name, fn)

for f in FAILURES:
    print("FAIL: " + f)
print(f"RESULT {PASSED} passed {len(FAILURES)} failed")
sys.exit(1 if FAILURES else 0)
