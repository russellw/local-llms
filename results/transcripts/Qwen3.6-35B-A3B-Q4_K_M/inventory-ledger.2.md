# inventory-ledger -- FIFO inventory ledger with fractional unit costs

passed: True   stopped: finish   steps: 9/26   edits: 3   test runs: 2   failing at end: 0/7

## step 1

I'll start by exploring the project structure and understanding the codebase.

    -> list_files({})

       README.md (39 lines)
       src/__init__.py (0 lines)
       src/ledger.py (59 lines)
       src/money.py (14 lines)

## step 2

Let me read the main files to understand the project.

    -> read_file({"path": "README.md"})

       # Inventory ledger
       
       Tracks stock received at a per-unit cost and issued out again, and reports the
       cost of what was issued.
       
       ## Units and money
       
       A unit cost is a decimal string with up to four decimal places, in **cents per
       unit** -- `"3.4567"` means 3.4567 cents for one unit. Quantities are whole
       units.
       
       Amounts of money that leave the module -- the return of `issue`, the return of
       `valuation` -- are **whole cents, as an `int`**.
       
       ## Costing
       
       Issues consume stock **first in, first out**: the oldest lot still holding
       stock is drawn down first, then the next, and so on. A lot may be partly
       consumed, in which case the remainder stays available at the same unit cost.
       
       ## Rounding
       
       This is the part that is easy to get wrong.
       
       The cost of an issue is computed **exactly** -- at full decimal prec... (truncated)

    -> read_file({"path": "src/ledger.py"})

       """A FIFO inventory ledger. See README.md for the rules."""
       
       from decimal import Decimal
       
       from .money import parse_rate, to_cents
       
       
       class InsufficientStock(Exception):
           """Raised when an issue asks for more than is on hand."""
       
       
       class Lot:
           def __init__(self, qty, rate):
               self.qty = qty
               self.rate = rate
       
           def __repr__(self):
               return f"Lot(qty={self.qty}, rate={self.rate})"
       
       
       class Ledger:
           def __init__(self):
               self.lots = []
       
           def receive(self, qty, rate):
               """Take in `qty` units at `rate` cents each."""
               if qty <= 0:
                   raise ValueError("qty must be positive")
               self.lots.append(Lot(qty, parse_rate(rate)))
       
           def on_hand(self):
               """Total units available."""
               return sum(lot.qty for lot in self.lots)
       
        ... (truncated)

## step 3

Let me read the money.py file.

    -> read_file({"path": "src/money.py"})

       """Money helpers. Costs are cents per unit, carried at full precision."""
       
       import math
       from decimal import Decimal
       
       
       def parse_rate(text):
           """Parse a per-unit cost such as '3.4567' into an exact value."""
           return Decimal(str(text))
       
       
       def to_cents(amount):
           """Round an exact amount of cents to a whole number of cents."""
           return int(math.floor(float(amount) + 0.5))

## step 4

Now let me run the tests to see what's failing.

    -> run_tests({})

       3/7 tests passed
       FAIL: issue_10_of_two_lots: cost of issuing 10 was 20, expected 10
       FAIL: valuation_after_issuing_10: valuation was 10, expected 20
       FAIL: issue_6_of_8: cost of issuing 6 was 11, expected 9
       FAIL: valuation_after_issuing_6: valuation was 2, expected 4

## step 5

I can see several bugs in the code:

1. **`issue` uses LIFO instead of FIFO**: `self.lots[-1]` takes from the last lot, but FIFO requires taking from the first (oldest) lot.
2. **`issue` has a bug**: `lot.qty -= remaining` should be `lot.qty -= take`.
3. **`to_cents` uses wrong rounding**: It uses "half up" (`math.floor(x + 0.5)`) but the README requires "half to even" rounding.

Let me fix these:

    -> replace_in_file({"path": "src/ledger.py", "old": "    def issue(self, qty):\n        \"\"\"Consume `qty` units, oldest first. Returns the cost in whole cents.\"\"\"\n        if qty <= 0:\n            raise ValueError(\"qty must be positive\")\n\n        total = 0\n        remaining = qty\n        while remaining > 0:\n            if not self.lots:\n                ... (630 chars)", "new": "    def issue(self, qty):\n        \"\"\"Consume `qty` units, oldest first. Returns the cost in whole cents.\"\"\"\n        if qty <= 0:\n            raise ValueError(\"qty must be positive\")\n\n        # Check if enough stock is available before consuming anything\n        if qty > self.on_hand():\n            r... (716 chars)"})

       replaced 1 occurrence in src/ledger.py

## step 6

Now let me fix the `to_cents` function to use half-to-even rounding. The `decimal` module has a `ROUND_HALF_EVEN` mode.

    -> replace_in_file({"path": "src/money.py", "old": "def to_cents(amount):\n    \"\"\"Round an exact amount of cents to a whole number of cents.\"\"\"\n    return int(math.floor(float(amount) + 0.5))", "new": "def to_cents(amount):\n    \"\"\"Round an exact amount of cents to a whole number of cents.\"\"\"\n    return int(Decimal(amount).quantize(Decimal('1'), rounding=ROUND_HALF_EVEN))"})

       replaced 1 occurrence in src/money.py

## step 7

I need to add the import for `ROUND_HALF_EVEN`. Let me fix that.

    -> replace_in_file({"path": "src/money.py", "old": "import math\nfrom decimal import Decimal", "new": "from decimal import Decimal, ROUND_HALF_EVEN"})

       replaced 1 occurrence in src/money.py

## step 8

Now let me run the tests again to see if the fixes work.

    -> run_tests({})

       7/7 tests passed
       all tests passed

## step 9

All 7 tests pass now. Here's a summary of the fixes:

1. **`src/ledger.py` — `issue` method**: Fixed three bugs:
   - Changed `self.lots[-1]` to `self.lots[0]` to implement FIFO (first-in, first-out) instead of LIFO.
   - Changed `lot.qty -= remaining` to `lot.qty -= take` so the lot quantity is decremented by the actual amount taken, not the remaining issue quantity.
   - Moved the `to_cents` call to after the loop so the total is computed at full decimal precision and rounded only once at the end, as the README requires.
   - Added a pre-check for `InsufficientStock` that leaves the ledger unchanged.

2. **`src/money.py` — `to_cents` function**: Replaced `math.floor(float(amount) + 0.5)` (half-up rounding) with `Decimal.quantize(Decimal('1'), rounding=ROUND_HALF_EVEN)` to implement the required "half to even" rounding behavior.

    -> finish({"summary": "Fixed FIFO ordering (lots[0] instead of lots[-1]), corrected lot quantity decrement (take instead of remaining), moved rounding to after the loop for exact computation, and replaced half-up rounding with half-to-even rounding."})

       ended
