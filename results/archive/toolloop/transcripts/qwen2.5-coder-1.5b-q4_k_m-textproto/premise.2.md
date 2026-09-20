# premise -- A join that only holds after a documented rule is applied

target hit: False   stopped: finish   steps: 4/12   tools: describe_table, count_rows, check_orphans, finish

## step 1

```json
{"tool": "describe_table", "args": {"table": "readings"}}
```

    -> describe_table({"table": "readings"})

## step 2

```json
{"tool": "count_rows", "args": {"table": "readings", "column": "site_ref", "op": "blank"}}
```

    -> count_rows({"table": "readings", "column": "site_ref", "op": "blank"})

## step 3

```json
{"tool": "check_orphans", "args": {"left_table": "readings", "left_column": "site_ref", "right_table": "premises", "right_column": "upn", "left_strip": "", "right_strip": ""}}
```

    -> check_orphans({"left_table": "readings", "left_column": "site_ref", "right_table": "premises", "right_column": "upn", "left_strip": "", "right_strip": ""})

## step 4

```json
{"tool": "finish", "args": {"summary": "There are 14 distinct site references that have no premise."}}
```

    -> finish({"summary": "There are 14 distinct site references that have no premise."})
