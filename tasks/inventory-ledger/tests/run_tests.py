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

def fifo_order():
    L = Ledger()
    L.receive(10, "1.0")
    L.receive(10, "2.0")
    eq(L.issue(10), 10, "cost of issuing 10 from the older 1.0c lot")


def fifo_leaves_the_newer_lot():
    L = Ledger()
    L.receive(10, "1.0")
    L.receive(10, "2.0")
    L.issue(10)
    eq(L.valuation(), 20, "valuation after the older lot is consumed")


# -- an issue may span lots --------------------------------------------

def issue_spanning_two_lots():
    L = Ledger()
    L.receive(3, "1.0")
    L.receive(5, "2.0")
    eq(L.issue(6), 9, "cost of 3 units at 1.0c plus 3 units at 2.0c")


def remainder_after_spanning_issue():
    L = Ledger()
    L.receive(3, "1.0")
    L.receive(5, "2.0")
    L.issue(6)
    eq(L.on_hand(), 2, "units left after issuing 6 of 8")


def partial_lot_keeps_its_rate():
    L = Ledger()
    L.receive(3, "1.0")
    L.receive(5, "2.0")
    L.issue(6)
    eq(L.valuation(), 4, "value of the 2 units left at 2.0c")


# -- rounding ----------------------------------------------------------

def rounds_once_not_per_lot():
    # Two lots of half a cent each. Exactly one cent in total, so the answer
    # is 1. Rounding each lot first gives 0 (half to even) or 2 (half up).
    L = Ledger()
    L.receive(1, "0.5")
    L.receive(1, "0.5")
    eq(L.issue(2), 1, "cost of two half-cent units rounded once")


def half_to_even_rounds_down():
    L = Ledger()
    L.receive(1, "2.5")
    eq(L.issue(1), 2, "2.5 cents rounded half to even")


def half_to_even_rounds_up():
    L = Ledger()
    L.receive(1, "3.5")
    eq(L.issue(1), 4, "3.5 cents rounded half to even")


def valuation_rounds_half_to_even():
    L = Ledger()
    L.receive(1, "2.5")
    eq(L.valuation(), 2, "valuation of 2.5 cents rounded half to even")


def four_decimal_places_are_exact():
    L = Ledger()
    L.receive(3, "3.4567")
    # 3 x 3.4567 = 10.3701 -> 10
    eq(L.issue(3), 10, "cost of 3 units at 3.4567c")


# -- failure leaves no trace -------------------------------------------

def overdraw_raises():
    L = Ledger()
    L.receive(5, "1.0")
    try:
        L.issue(10)
    except InsufficientStock:
        return
    raise AssertionError("issuing more than on hand did not raise InsufficientStock")


def overdraw_consumes_nothing():
    L = Ledger()
    L.receive(5, "1.0")
    try:
        L.issue(10)
    except InsufficientStock:
        pass
    eq(L.on_hand(), 5, "units on hand after a failed issue")


def retry_after_overdraw_succeeds():
    L = Ledger()
    L.receive(5, "1.0")
    L.receive(5, "2.0")
    try:
        L.issue(20)
    except InsufficientStock:
        pass
    eq(L.issue(5), 5, "cost of retrying with a quantity that fits")


# -- a longer sequence -------------------------------------------------

def running_sequence():
    L = Ledger()
    L.receive(100, "1.2345")
    L.receive(50, "2.5")
    L.receive(25, "0.0001")
    eq(L.issue(120), 173, "cost of 100 at 1.2345c plus 20 at 2.5c")
    eq(L.on_hand(), 55, "units left")
    # 30 x 2.5 = 75, 25 x 0.0001 = 0.0025 -> 75.0025 -> 75
    eq(L.valuation(), 75, "value of what is left")


CHECKS = [
    ("fifo_order", fifo_order),
    ("fifo_leaves_the_newer_lot", fifo_leaves_the_newer_lot),
    ("issue_spanning_two_lots", issue_spanning_two_lots),
    ("remainder_after_spanning_issue", remainder_after_spanning_issue),
    ("partial_lot_keeps_its_rate", partial_lot_keeps_its_rate),
    ("rounds_once_not_per_lot", rounds_once_not_per_lot),
    ("half_to_even_rounds_down", half_to_even_rounds_down),
    ("half_to_even_rounds_up", half_to_even_rounds_up),
    ("valuation_rounds_half_to_even", valuation_rounds_half_to_even),
    ("four_decimal_places_are_exact", four_decimal_places_are_exact),
    ("overdraw_raises", overdraw_raises),
    ("overdraw_consumes_nothing", overdraw_consumes_nothing),
    ("retry_after_overdraw_succeeds", retry_after_overdraw_succeeds),
    ("running_sequence", running_sequence),
]

for name, fn in CHECKS:
    check(name, fn)

for f in FAILURES:
    print("FAIL: " + f)
print(f"RESULT {PASSED} passed {len(FAILURES)} failed")
sys.exit(1 if FAILURES else 0)
