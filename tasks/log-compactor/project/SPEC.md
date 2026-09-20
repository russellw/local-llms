# Log compaction

Reduces a stream of records to the current value of each key.

## Input

An iterable of `(timestamp, key, value)`. Timestamps are integers and are **not
sorted** -- a record may arrive out of order. The stream is large and may be a
generator; it can only be walked once.

## Output

`compact(records, min_count)` returns a list of `(key, value)`.

- A key appears in the output only if it occurs in the stream **at least**
  `min_count` times. `min_count=1` keeps everything.
- Its value is the one from its record with the **highest timestamp**. If two
  records for a key share the highest timestamp, the one that appeared **later
  in the stream** wins.
- The output is ordered by where each key **first appeared** in the stream --
  not alphabetically, and not by timestamp.

## Cost

This is the part that is easy to get wrong.

The stream can hold millions of records, and compaction must stay **linear** in
the number of records: one pass, with per-record work that does not depend on
how many distinct keys have been seen so far. Searching the keys accumulated
so far to find out whether a key is new -- `list.index`, `in` against a list, a
scan of the results built up -- turns one pass into a quadratic one, and the
test suite is large enough that it will not finish.
