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
        # Checked before anything is mutated: a failed issue must leave the
        # ledger untouched so a caller can retry with less.
        if self.on_hand() < qty:
            raise InsufficientStock(f"short by {qty - self.on_hand()} units")

        total = Decimal(0)
        remaining = qty
        while remaining > 0:
            lot = self.lots[0]
            take = min(lot.qty, remaining)
            total += Decimal(take) * lot.rate
            lot.qty -= take
            remaining -= take
            if lot.qty <= 0:
                self.lots.pop(0)
        # Rounded once, at the end, on the exact total.
        return to_cents(total)

    def valuation(self):
        """Cost of everything still on hand, in whole cents."""
        total = Decimal(0)
        for lot in self.lots:
            total += Decimal(lot.qty) * lot.rate
        return to_cents(total)
