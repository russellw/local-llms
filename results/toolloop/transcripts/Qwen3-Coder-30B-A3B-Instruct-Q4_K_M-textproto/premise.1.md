# premise -- A join that only holds after a documented rule is applied

target hit: False   stopped: finish   steps: 7/12   tools: list_tables, describe_table, check_orphans, record_finding, finish

## step 1

```json
{"tool": "list_tables", "args": {}}
```

    -> list_tables({})

## step 2

```json
{"tool": "describe_table", "args": {"table": "readings"}}
```

    -> describe_table({"table": "readings"})

## step 3

```json
{"tool": "describe_table", "args": {"table": "premises"}}
```

    -> describe_table({"table": "premises"})

## step 4

```json
{"tool": "check_orphans", "args": {"left_table": "readings", "left_column": "site_ref", "right_table": "premises", "right_column": "upn"}}
```

    -> check_orphans({"left_table": "readings", "left_column": "site_ref", "right_table": "premises", "right_column": "upn"})

## step 5

```json
{"tool": "record_finding", "args": {"title": "All 14 distinct site references in readings table have no matching premise in premises table.", "evidence_tool": "check_orphans", "evidence_args": {"left_table": "readings", "left_column": "site_ref", "right_table": "premises", "right_column": "upn"}, "expected": "0"}}
```

    -> record_finding({"title": "All 14 distinct site references in readings table have no matching premise in premises table.", "evidence_tool": "check_orphans", "evidence_args": {"left_table": "readings", "left_column": "site_ref", "right_table": "premises", "right_column": "upn"}, "expected": "0"})

## step 6

```json
{"tool": "record_finding", "args": {"title": "14 distinct site references in readings table have no matching premise in premises table.", "evidence_tool": "check_orphans", "evidence_args": {"left_table": "readings", "left_column": "site_ref", "right_table": "premises", "right_column": "upn"}, "expected": "14"}}
```

    -> record_finding({"title": "14 distinct site references in readings table have no matching premise in premises table.", "evidence_tool": "check_orphans", "evidence_args": {"left_table": "readings", "left_column": "site_ref", "right_table": "premises", "right_column": "upn"}, "expected": "14"})

## step 7

```json
{"tool": "finish", "args": {"summary": "Found that 14 distinct site references in the readings table have no matching premise in the premises table, confirming a data integrity issue where all readings lack corresponding premises."}}
```

    -> finish({"summary": "Found that 14 distinct site references in the readings table have no matching premise in the premises table, confirming a data integrity issue where all readings lack corresponding premises."})
