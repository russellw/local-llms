Write a function:

```python
def parse_csv(text: str) -> list[list[str]]
```

that parses RFC 4180 style CSV into a list of rows, each row a list of field
strings. **Do not import the `csv` module** (or any third-party library) —
write the parser yourself.

Rules:

- Fields are separated by commas, records by newlines. Accept `\n`, `\r\n`, and
  a bare `\r` as record separators; the returned fields never contain the
  separator that ended their record.
- A field may be wrapped in double quotes. Inside a quoted field, a comma, a
  newline, and a carriage return are literal data, and two consecutive double
  quotes `""` mean one literal double quote.
- Quotes only have meaning at the very start of a field. A field like
  `say "hi"` is unquoted data and keeps its quote characters verbatim.
- Whitespace is significant and is never stripped.
- An empty field is the empty string. A row of `a,,b` has three fields.
- A trailing newline at the end of the input does **not** create an extra empty
  row, but a blank line in the middle of the input is a row with one empty
  field.
- The empty string parses to an empty list.
- If the input ends while a quoted field is still open, raise `ValueError`.

Return only `list` objects containing `str` values.
