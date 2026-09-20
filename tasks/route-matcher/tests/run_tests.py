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

def static_beats_param_registered_later():
    r = build(("/users/:id", "param"), ("/users/me", "static"))
    eq(r.match("/users/me")[0], "static", "handler for /users/me")


def static_beats_param_registered_earlier():
    r = build(("/users/me", "static"), ("/users/:id", "param"))
    eq(r.match("/users/me")[0], "static", "handler for /users/me")


def param_still_matches_other_paths():
    r = build(("/users/:id", "param"), ("/users/me", "static"))
    eq(r.match("/users/42"), ("param", {"id": "42"}), "match for /users/42")


def param_beats_wildcard():
    r = build(("/*rest", "wild"), ("/users/:id", "param"))
    eq(r.match("/users/42")[0], "param", "handler for /users/42")


def specificity_is_decided_at_the_first_differing_segment():
    r = build(("/:a/:b/c", "params"), ("/x/:b/c", "static_first"))
    eq(r.match("/x/y/c")[0], "static_first", "handler for /x/y/c")


def equal_specificity_falls_back_to_registration_order():
    r = build(("/:a/b", "first"), ("/:c/b", "second"))
    eq(r.match("/z/b")[0], "first", "handler when both are equally specific")


# -- captures ----------------------------------------------------------

def param_names_drop_the_marker():
    r = build(("/users/:id", "h"),)
    eq(r.match("/users/7")[1], {"id": "7"}, "captured params")


def two_params():
    r = build(("/:org/repos/:name", "h"),)
    eq(r.match("/acme/repos/tools")[1], {"org": "acme", "name": "tools"},
       "captured params")


def wildcard_captures_all_remaining_segments():
    r = build(("/files/*path", "h"),)
    eq(r.match("/files/a/b/c.txt")[1], {"path": "a/b/c.txt"}, "captured wildcard")


def wildcard_captures_one_segment():
    r = build(("/files/*path", "h"),)
    eq(r.match("/files/a.txt")[1], {"path": "a.txt"}, "captured wildcard")


def wildcard_can_capture_nothing():
    r = build(("/files/*path", "h"),)
    eq(r.match("/files")[1], {"path": ""}, "captured wildcard for a bare prefix")


# -- trailing slashes and the root -------------------------------------

def trailing_slash_is_insignificant():
    r = build(("/users/me", "h"),)
    eq(r.match("/users/me/")[0], "h", "handler for a path with a trailing slash")


def root_matches_the_root_pattern():
    r = build(("/", "root"),)
    eq(r.match("/")[0], "root", "handler for /")


def root_does_not_match_a_one_segment_pattern():
    r = build(("/:id", "param"),)
    eq(r.match("/"), None, "match for / against a single-parameter pattern")


# -- no match ----------------------------------------------------------

def unmatched_returns_none():
    r = build(("/users/:id", "h"),)
    eq(r.match("/orders/1"), None, "match for an unregistered path")


def too_many_segments_do_not_match_a_param_route():
    r = build(("/users/:id", "h"),)
    eq(r.match("/users/1/edit"), None, "match for a deeper path")


CHECKS = [
    ("static_beats_param_registered_later", static_beats_param_registered_later),
    ("static_beats_param_registered_earlier", static_beats_param_registered_earlier),
    ("param_still_matches_other_paths", param_still_matches_other_paths),
    ("param_beats_wildcard", param_beats_wildcard),
    ("specificity_is_decided_at_the_first_differing_segment",
     specificity_is_decided_at_the_first_differing_segment),
    ("equal_specificity_falls_back_to_registration_order",
     equal_specificity_falls_back_to_registration_order),
    ("param_names_drop_the_marker", param_names_drop_the_marker),
    ("two_params", two_params),
    ("wildcard_captures_all_remaining_segments", wildcard_captures_all_remaining_segments),
    ("wildcard_captures_one_segment", wildcard_captures_one_segment),
    ("wildcard_can_capture_nothing", wildcard_can_capture_nothing),
    ("trailing_slash_is_insignificant", trailing_slash_is_insignificant),
    ("root_matches_the_root_pattern", root_matches_the_root_pattern),
    ("root_does_not_match_a_one_segment_pattern", root_does_not_match_a_one_segment_pattern),
    ("unmatched_returns_none", unmatched_returns_none),
    ("too_many_segments_do_not_match_a_param_route", too_many_segments_do_not_match_a_param_route),
]

for name, fn in CHECKS:
    check(name, fn)

for f in FAILURES:
    print("FAIL: " + f)
print(f"RESULT {PASSED} passed {len(FAILURES)} failed")
sys.exit(1 if FAILURES else 0)
