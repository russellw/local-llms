"""Hidden test suite. Prints curated one-line failures and a RESULT tally.

Never print a traceback: the source line would hand the model the assertion it
is meant to satisfy. Every check reports only what it expected and what it got.
"""

import sys

from src.ledger import Ledger, InsufficientStock

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


# -- oldest stock is consumed first ------------------------------------

def issue_10_of_two_lots():
    L = Ledger()
    L.receive(10, "1.0")
    L.receive(10, "2.0")
    eq(L.issue(10), 10, "cost of issuing 10")


def valuation_after_issuing_10():
    L = Ledger()
    L.receive(10, "1.0")
    L.receive(10, "2.0")
    L.issue(10)
    eq(L.valuation(), 20, "valuation")


# -- an issue may span lots --------------------------------------------

def issue_6_of_8():
    L = Ledger()
    L.receive(3, "1.0")
    L.receive(5, "2.0")
    eq(L.issue(6), 9, "cost of issuing 6")


def on_hand_after_issuing_6():
    L = Ledger()
    L.receive(3, "1.0")
    L.receive(5, "2.0")
    L.issue(6)
    eq(L.on_hand(), 2, "units on hand")


def valuation_after_issuing_6():
    L = Ledger()
    L.receive(3, "1.0")
    L.receive(5, "2.0")
    L.issue(6)
    eq(L.valuation(), 4, "valuation")


# -- rounding ----------------------------------------------------------

def two_lots_of_half_a_cent():
    # Two lots of half a cent each. Exactly one cent in total, so the answer
    # is 1. Rounding each lot first gives 0 (half to even) or 2 (half up).
    L = Ledger()
    L.receive(1, "0.5")
    L.receive(1, "0.5")
    eq(L.issue(2), 1, "cost of issuing 2")


def issue_one_unit_at_2_5():
    L = Ledger()
    L.receive(1, "2.5")
    eq(L.issue(1), 2, "cost of issuing 1")


def issue_one_unit_at_3_5():
    L = Ledger()
    L.receive(1, "3.5")
    eq(L.issue(1), 4, "cost of issuing 1")


def valuation_of_one_unit_at_2_5():
    L = Ledger()
    L.receive(1, "2.5")
    eq(L.valuation(), 2, "valuation")


def issue_three_units_at_3_4567():
    L = Ledger()
    L.receive(3, "3.4567")
    # 3 x 3.4567 = 10.3701 -> 10
    eq(L.issue(3), 10, "cost of issuing 3")


# -- failure leaves no trace -------------------------------------------

def overdraw_raises():
    L = Ledger()
    L.receive(5, "1.0")
    try:
        L.issue(10)
    except InsufficientStock:
        return
    raise AssertionError("issuing more than on hand did not raise InsufficientStock")


def on_hand_after_an_overdraw():
    L = Ledger()
    L.receive(5, "1.0")
    try:
        L.issue(10)
    except InsufficientStock:
        pass
    eq(L.on_hand(), 5, "units on hand after a failed issue")


def issue_after_an_overdraw():
    L = Ledger()
    L.receive(5, "1.0")
    L.receive(5, "2.0")
    try:
        L.issue(20)
    except InsufficientStock:
        pass
    eq(L.issue(5), 5, "cost of the second issue")


# -- a longer sequence -------------------------------------------------

def longer_sequence():
    L = Ledger()
    L.receive(100, "1.2345")
    L.receive(50, "2.5")
    L.receive(25, "0.0001")
    eq(L.issue(120), 173, "cost of issuing 120")
    eq(L.on_hand(), 55, "units on hand")
    # 30 x 2.5 = 75, 25 x 0.0001 = 0.0025 -> 75.0025 -> 75
    eq(L.valuation(), 75, "valuation")


CHECKS = [
    ("two_lots_of_half_a_cent", two_lots_of_half_a_cent),
    ("issue_one_unit_at_2_5", issue_one_unit_at_2_5),
    ("issue_one_unit_at_3_5", issue_one_unit_at_3_5),
    ("valuation_of_one_unit_at_2_5", valuation_of_one_unit_at_2_5),
    ("on_hand_after_an_overdraw", on_hand_after_an_overdraw),
    ("issue_after_an_overdraw", issue_after_an_overdraw),
    ("longer_sequence", longer_sequence),
]

for name, fn in CHECKS:
    check(name, fn)

for f in FAILURES:
    print("FAIL: " + f)
print(f"RESULT {PASSED} passed {len(FAILURES)} failed")
sys.exit(1 if FAILURES else 0)
