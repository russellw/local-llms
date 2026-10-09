# inventory-ledger -- FIFO inventory ledger with fractional unit costs

passed: True   stopped: finish   steps: 8/26   edits: 2   test runs: 1   failing at end: 0/7

## step 1

Let's start by exploring the project structure.

    -> list_files({})

       README.md (39 lines)
       src/__init__.py (0 lines)
       src/ledger.py (59 lines)
       src/money.py (14 lines)

## step 2

Small project. Let me try reading all the files.

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

Let's read money.py.

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

Now I can see the code. Comparing it against the README, I can spot several bugs:

1. **`issue` uses `self.lots[-1]`** — that's the *newest* lot (LIFO), but the README says FIFO (oldest first).
2. **`issue` rounds each lot's contribution** (`total += to_cents(...)`) — the README says compute exactly across all lots and round only once at the end.
3. **`to_cents` uses `math.floor(float(x) + 0.5)`** — that's half-up rounding via float, but the README requires half-to-even (banker's rounding).
4. **`issue` mutates the ledger as it goes** — if it runs out of stock mid-loop, the ledger is left partially consumed, but the README says it must be left exactly as it was.
5. Minor: `lot.qty -= remaining` should be `lot.qty -= take`.

Let me fix `money.py` first:

    -> replace_in_file({"path": "src/money.py", "old": "import math\nfrom decimal import Decimal\n\n\ndef parse_rate(text):\n    \"\"\"Parse a per-unit cost such as '3.4567' into an exact value.\"\"\"\n    return Decimal(str(text))\n\n\ndef to_cents(amount):\n    \"\"\"Round an exact amount of cents to a whole number of cents.\"\"\"\n    return int(math.floor(float(amount) + 0... (304 chars)", "new": "from decimal import Decimal, ROUND_HALF_EVEN\n\n\ndef parse_rate(text):\n    \"\"\"Parse a per-unit cost such as '3.4567' into an exact value.\"\"\"\n    return Decimal(str(text))\n\n\ndef to_cents(amount):\n    \"\"\"Round an exact amount of cents to a whole number of cents.\"\"\"\n    return int(Decimal(amount).quantiz... (342 chars)"})

       replaced 1 occurrence in src/money.py

## step 5

Now the `issue` method in `ledger.py`:

    -> replace_in_file({"path": "src/ledger.py", "old": "        total = 0\n        remaining = qty\n        while remaining > 0:\n            if not self.lots:\n                raise InsufficientStock(f\"short by {remaining} units\")\n            lot = self.lots[-1]\n            take = min(lot.qty, remaining)\n            total += to_cents(Decimal(take) * lot.rat... (447 chars)", "new": "        if self.on_hand() < qty:\n            raise InsufficientStock(f\"short by {qty - self.on_hand()} units\")\n\n        total = Decimal(0)\n        remaining = qty\n        while remaining > 0:\n            lot = self.lots[0]\n            take = min(lot.qty, remaining)\n            total += Decimal(take)... (462 chars)"})

       replaced 1 occurrence in src/ledger.py

## step 6

`valuation` already accumulates exactly and rounds once, so it's fine now that `to_cents` is correct. Let me run the tests:

    -> run_tests({})

       7/7 tests passed
       all tests passed

## step 7

All 7 tests pass. Let me do a final sanity check on the modified files:

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

## step 8

The code is clean and the full suite passes.

    -> finish({"summary": "Fixed the FIFO ledger: `issue` now draws from the oldest lot first (was LIFO), accumulates cost at full Decimal precision and rounds once at the end (was rounding per lot), checks stock before mutating so a failed issue leaves the ledger untouched, and `to_cents` now uses exact Decimal half-to-even ... (334 chars)"})

       ended
