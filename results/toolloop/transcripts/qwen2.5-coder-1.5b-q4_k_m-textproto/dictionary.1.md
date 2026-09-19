# dictionary -- Find states no document allows

target hit: False   stopped: finish   steps: 6/10   tools: describe_table, sample_column, distinct_values, count_rows, record_finding, finish

## step 1

```json
{"tool": "describe_table", "args": {"table": "readings"}}
```

    -> describe_table({"table": "readings"})

## step 2

```json
{"tool": "sample_column", "args": {"table": "readings", "column": "status", "n": 10}}
```

    -> sample_column({"table": "readings", "column": "status", "n": 10})

## step 3

```json
{"tool": "distinct_values", "args": {"table": "readings", "column": "status"}}
```

    -> distinct_values({"table": "readings", "column": "status"})

## step 4

```json
{"tool": "count_rows", "args": {"table": "readings", "column": "status", "op": "not_in", "value": "ACTUAL, CUSTOMER, EST, ESTIMATED"}}
```

    -> count_rows({"table": "readings", "column": "status", "op": "not_in", "value": "ACTUAL, CUSTOMER, EST, ESTIMATED"})

## step 5

```json
{"tool": "record_finding", "args": {"title": "The status column has 2 rows that are not one of the valid states defined in the dataset.", "evidence_tool": "count_rows", "evidence_args": {"table": "readings", "column": "status", "op": "not_in", "value": "ACTUAL, CUSTOMER, EST, ESTIMATED"}, "expected": "2"}}
```

    -> record_finding({"title": "The status column has 2 rows that are not one of the valid states defined in the dataset.", "evidence_tool": "count_rows", "evidence_args": {"table": "readings", "column": "status", "op": "not_in", "value": "ACTUAL, CUSTOMER, EST, ESTIMATED"}, "expected": "2"})

## step 6

```json
{"tool": "finish", "args": {"summary": "The status column has 2 rows that are not one of the valid states defined in the dataset."}}
```

    -> finish({"summary": "The status column has 2 rows that are not one of the valid states defined in the dataset."})
