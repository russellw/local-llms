Write a function:

```python
def evaluate(expr: str) -> float
```

that parses and evaluates an arithmetic expression and returns the result as a
`float`. **Do not use `eval`, `exec`, `compile`, `ast`, or any third-party
library** — write a real parser.

The grammar:

- Number literals: digits with an optional decimal point, e.g. `3`, `3.5`,
  `.5`, `10.`. No exponent notation, no sign as part of the literal.
- Binary operators `+`, `-`, `*`, `/`, `%`, and `**`.
- Precedence from loosest to tightest: `+ -`, then `* / %`, then unary `-` and
  unary `+`, then `**`.
- `+ - * / %` are left-associative. `**` is right-associative, so
  `2 ** 3 ** 2` is 512, not 64.
- `**` binds tighter than unary minus, so `-2 ** 2` is `-4.0`. Unary minus
  binds tighter than `*`, so `-2 * 3` is `-6.0`. Unary operators may stack:
  `--3` is `3.0`.
- Parentheses override precedence and may nest arbitrarily.
- Whitespace between tokens is insignificant and may appear anywhere.
- `/` is true division, `%` follows Python's sign convention for `%` on floats.

Errors:

- Division or modulo by zero raises `ZeroDivisionError`.
- Any malformed input — an unknown character, unbalanced parentheses, a missing
  operand, two numbers in a row, an empty expression — raises `ValueError`.
