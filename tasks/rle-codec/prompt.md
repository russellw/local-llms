Write two functions:

```python
def rle_encode(s: str) -> str
def rle_decode(s: str) -> str
```

`rle_encode` compresses a string by replacing each maximal run of N identical
characters with that character followed by the decimal count N. The count is
**always** written, even when N is 1. For example `"aaabbc"` becomes `"a3b2c1"`.

The input to `rle_encode` never contains digits, but may contain any other
characters (spaces, punctuation, newlines, non-ASCII). Runs may be longer than
9 characters, so counts can have multiple digits.

`rle_decode` is the exact inverse: for every valid input `s`,
`rle_decode(rle_encode(s)) == s`. The empty string encodes to the empty string
and decodes back to the empty string.
