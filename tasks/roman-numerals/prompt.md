Write two functions:

```python
def to_roman(n: int) -> str
def from_roman(s: str) -> int
```

`to_roman` converts an integer in the range 1 to 3999 inclusive into a standard
Roman numeral using uppercase letters and subtractive notation, so 4 is `"IV"`
(not `"IIII"`), 9 is `"IX"`, 40 is `"XL"`, 90 is `"XC"`, 400 is `"CD"` and 900
is `"CM"`. If `n` is outside 1..3999, or is not an `int`, raise `ValueError`.

`from_roman` parses a well-formed uppercase Roman numeral back to an integer.
It is the inverse of `to_roman` over the whole supported range.

Do not use any third-party libraries.
