# shapes -- Count blank values in a column you can only sample

target hit: True   stopped: finish   steps: 3/8   tools: count_rows, record_finding, finish

## step 1

```json
{
  "name": "count_rows",
  "arguments": {
    "table": "premises",
    "column": "address",
    "op": "blank",
    "value": ""
  }
}
```

    -> count_rows({"table": "premises", "column": "address", "op": "blank", "value": ""})

## step 2

```json
{
  "name": "record_finding",
  "arguments": {
    "title": "There are 2 blank rows in the 'address' column of the 'premises' table.",
    "evidence_tool": "count_rows",
    "evidence_args": {
      "table": "premises",
      "column": "address",
      "op": "blank",
      "value": ""
    },
    "expected": "2"
  }
}
```

    -> record_finding({"title": "There are 2 blank rows in the 'address' column of the 'premises' table.", "evidence_tool": "count_rows", "evidence_args": {"table": "premises", "column": "address", "op": "blank", "value": ""}, "expected": "2"})

## step 3

```json
{
  "name": "finish",
  "arguments": {
    "summary": "There are 2 blank rows in the 'address' column of the 'premises' table."
  }
}
```

    -> finish({"summary": "There are 2 blank rows in the 'address' column of the 'premises' table."})
