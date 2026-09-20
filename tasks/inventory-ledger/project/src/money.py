"""Money helpers. Costs are cents per unit, carried at full precision."""

import math
from decimal import Decimal


def parse_rate(text):
    """Parse a per-unit cost such as '3.4567' into an exact value."""
    return Decimal(str(text))


def to_cents(amount):
    """Round an exact amount of cents to a whole number of cents."""
    return int(math.floor(float(amount) + 0.5))
