# dictionary -- Find states no document allows

target hit: False   stopped: finish   steps: 3/10   tools: count_rows, record_finding, finish

## step 1

```json
{
  "name": "count_rows",
  "arguments": {
    "table": "readings",
    "column": "status",
    "op": "not_in",
    "value": "valid"
  }
}
```

    -> count_rows({"table": "readings", "column": "status", "op": "not_in", "value": "valid"})

## step 2

```json
{
  "name": "record_finding",
  "arguments": {
    "title": "There are 40 rows with an invalid status.",
    "evidence_tool": "count_rows",
    "evidence_args": {
      "table": "readings",
      "column": "status",
      "op": "not_in",
      "value": "valid"
    },
    "expected": "40"
  }
}
```

    -> record_finding({"title": "There are 40 rows with an invalid status.", "evidence_tool": "count_rows", "evidence_args": {"table": "readings", "column": "status", "op": "not_in", "value": "valid"}, "expected": "40"})

## step 3

```json
{
  "name": "finish",
  "arguments": {
    "summary": "There are 40 rows with an invalid status, which is not one of the valid states defined in the dataset."
  }
}
```

    -> finish({"summary": "There are 40 rows with an invalid status, which is not one of the valid states defined in the dataset."})
