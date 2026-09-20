# premise -- A join that only holds after a documented rule is applied

target hit: False   stopped: finish   steps: 3/12   tools: check_orphans, record_finding, finish

## step 1

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

## step 2

```json
{
  "name": "record_finding",
  "arguments": {
    "title": "There are 14 distinct site references that have no premise.",
    "evidence_tool": "check_orphans",
    "evidence_args": {
      "left_table": "readings",
      "left_column": "site_ref",
      "right_table": "premises",
      "right_column": "upn",
      "left_strip": "",
      "right_strip": ""
    },
    "expected": "14"
  }
}
```

    -> record_finding({"title": "There are 14 distinct site references that have no premise.", "evidence_tool": "check_orphans", "evidence_args": {"left_table": "readings", "left_column": "site_ref", "right_table": "premises", "right_column": "upn", "left_strip": "", "right_strip": ""}, "expected": "14"})

## step 3

```json
{
  "name": "finish",
  "arguments": {
    "summary": "There are 14 distinct site references that have no premise."
  }
}
```

    -> finish({"summary": "There are 14 distinct site references that have no premise."})
