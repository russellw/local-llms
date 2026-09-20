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

The cost of an issue is computed **exactly** -- at full decimal precision,
across every lot the issue draws from -- and is rounded to whole cents **once,
at the end**. Do not round each lot's contribution and add up the rounded
figures; the two differ, and only the first is correct.

Rounding is **half to even**: a value exactly halfway between two whole cents
goes to the even one. `2.5` rounds to `2`, `3.5` rounds to `4`. This applies to
`valuation` as well.

## Failure

`issue` with a quantity larger than the stock on hand raises
`InsufficientStock` **and leaves the ledger exactly as it was**. A caller that
catches the error and retries with a smaller quantity must not find that stock
has already been consumed.
