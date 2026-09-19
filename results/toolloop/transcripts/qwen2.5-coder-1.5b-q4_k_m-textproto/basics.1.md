# basics -- Find the impossible values in a numeric column

target hit: True   stopped: finish   steps: 4/8   tools: count_rows, distinct_values, record_finding, finish

## step 1

```json
{"tool": "count_rows", "args": {"table": "readings", "column": "kwh", "op": "<", "value": "0"}}
```

    -> count_rows({"table": "readings", "column": "kwh", "op": "<", "value": "0"})

## step 2

```json
{"tool": "distinct_values", "args": {"table": "readings", "column": "kwh"}}
```

    -> distinct_values({"table": "readings", "column": "kwh"})

## step 3

```json
{"tool": "record_finding", "args": {"title": "There are 3 rows with negative kwh readings.", "evidence_tool": "count_rows", "evidence_args": {"table": "readings", "column": "kwh", "op": "<", "value": "0"}, "expected": "3"}}
```

    -> record_finding({"title": "There are 3 rows with negative kwh readings.", "evidence_tool": "count_rows", "evidence_args": {"table": "readings", "column": "kwh", "op": "<", "value": "0"}, "expected": "3"})

## step 4

```json
{"tool": "finish", "args": {"summary": "There are 3 rows with negative kwh readings."}}
```

    -> finish({"summary": "There are 3 rows with negative kwh readings."})
