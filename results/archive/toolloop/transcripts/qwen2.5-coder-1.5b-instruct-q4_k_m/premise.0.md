# premise -- A join that only holds after a documented rule is applied

target hit: False   stopped: finish   steps: 3/12   tools: count_rows, check_orphans, finish

## step 1

```json
{
  "name": "count_rows",
  "arguments": {
    "table": "readings",
    "column": "site_ref",
    "op": "not_blank",
    "value": ""
  }
}
```

    -> count_rows({"table": "readings", "column": "site_ref", "op": "not_blank", "value": ""})

## step 2

```json
{
  "name": "check_orphans",
  "arguments": {
    "left_table": "readings",
    "left_column": "site_ref",
    "right_table": "premises",
    "right_column": "upn",
    "left_strip": "",
    "right_strip": ""
  }
}
```

    -> check_orphans({"left_table": "readings", "left_column": "site_ref", "right_table": "premises", "right_column": "upn", "left_strip": "", "right_strip": ""})

## step 3

```json
{
  "name": "finish",
  "arguments": {
    "summary": "There are 14 distinct site references that have no corresponding premise."
  }
}
```

    -> finish({"summary": "There are 14 distinct site references that have no corresponding premise."})
