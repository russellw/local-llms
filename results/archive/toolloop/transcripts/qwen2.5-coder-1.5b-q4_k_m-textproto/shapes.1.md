# shapes -- Count blank values in a column you can only sample

target hit: False   stopped: budget   steps: 8/8   tools: count_rows, list_documents, record_finding, sample_column, distinct_values

## step 1

```json
{"tool": "count_rows", "args": {"table": "readings", "column": "premises.address", "op": "blank"}}
```

    -> count_rows({"table": "readings", "column": "premises.address", "op": "blank"})

## step 2

```json
{"tool": "list_documents"}
```

    -> list_documents({})

## step 3

```json
{"tool": "record_finding", "args": {"title": "Blank premises.address values are not allowed", "evidence_tool": "count_rows", "evidence_args": {"table": "readings", "column": "premises.address", "op": "blank"}, "expected": "0"}}
```

    -> record_finding({"title": "Blank premises.address values are not allowed", "evidence_tool": "count_rows", "evidence_args": {"table": "readings", "column": "premises.address", "op": "blank"}, "expected": "0"})

## step 4

```json
{"tool": "sample_column", "args": {"table": "readings", "column": "premises.address", "n": 1}}
```

    -> sample_column({"table": "readings", "column": "premises.address", "n": 1})

## step 5

```json
{"tool": "distinct_values", "args": {"table": "readings", "column": "premises.address"}}
```

    -> distinct_values({"table": "readings", "column": "premises.address"})

## step 6

```json
{"tool": "count_rows", "args": {"table": "readings", "column": "premises.address", "op": "blank"}}
```

    -> count_rows({"table": "readings", "column": "premises.address", "op": "blank"})

## step 7

```json
{"tool": "sample_column", "args": {"table": "readings", "column": "premises.address", "n": 1}}
```

    -> sample_column({"table": "readings", "column": "premises.address", "n": 1})

## step 8

```json
{"tool": "distinct_values", "args": {"table": "readings", "column": "premises.address"}}
```

    -> distinct_values({"table": "readings", "column": "premises.address"})
