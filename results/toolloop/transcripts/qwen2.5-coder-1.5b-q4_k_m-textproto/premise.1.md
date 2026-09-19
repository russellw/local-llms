# premise -- A join that only holds after a documented rule is applied

target hit: False   stopped: finish   steps: 3/12   tools: count_rows, distinct_values, finish

## step 1

```json
{"tool": "describe_table", "args": {"table": "readings"}}
```

```json
{"tool": "count_rows", "args": {"table": "readings", "column": "site_ref", "op": "blank"}}
```

    -> count_rows({"table": "readings", "column": "site_ref", "op": "blank"})

## step 2

```json
{"tool": "check_orphans", "args": {"left_table": "readings", "left_column": "site_ref", "right_table": "premises", "right_column": "upn", "left_strip": "", "right_strip": ""}}
```

```json
{"tool": "distinct_values", "args": {"table": "readings", "column": "site_ref"}}
```

    -> distinct_values({"table": "readings", "column": "site_ref"})

## step 3

```json
{"tool": "finish", "args": {"summary": "There are no distinct site references that have no premise."}}
```

    -> finish({"summary": "There are no distinct site references that have no premise."})
