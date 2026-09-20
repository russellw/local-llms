"""Money helpers. Costs are cents per unit, carried at full precision."""

from decimal import Decimal, ROUND_HALF_EVEN


def parse_rate(text):
    """Parse a per-unit cost such as '3.4567' into an exact value."""
    return Decimal(str(text))


def to_cents(amount):
    """Round an exact amount of cents to a whole number of cents.

    Half to even, per README.md, and on the exact value -- going through float
    would let binary error decide the ties this is supposed to decide.
    """
    return int(Decimal(amount).quantize(Decimal(1), rounding=ROUND_HALF_EVEN))
