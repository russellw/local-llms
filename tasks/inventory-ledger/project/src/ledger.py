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

    def issue(self, qty):
        """Consume `qty` units, oldest first. Returns the cost in whole cents."""
        if qty <= 0:
            raise ValueError("qty must be positive")

        total = 0
        remaining = qty
        while remaining > 0:
            if not self.lots:
                raise InsufficientStock(f"short by {remaining} units")
            lot = self.lots[-1]
            take = min(lot.qty, remaining)
            total += to_cents(Decimal(take) * lot.rate)
            lot.qty -= remaining
            remaining -= take
            if lot.qty <= 0:
                self.lots.pop()
        return total

    def valuation(self):
        """Cost of everything still on hand, in whole cents."""
        total = Decimal(0)
        for lot in self.lots:
            total += Decimal(lot.qty) * lot.rate
        return to_cents(total)
