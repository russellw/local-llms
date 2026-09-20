# shapes -- Count blank values in a column you can only sample

target hit: True   stopped: finish   steps: 7/8   tools: list_tables, describe_table, count_rows, record_finding, finish

## step 1

```json
{"tool": "list_tables", "args": {}}
```

    -> list_tables({})

## step 2

```json
{"tool": "describe_table", "args": {"table": "premises"}}
```

    -> describe_table({"table": "premises"})

## step 3

```json
{"tool": "count_rows", "args": {"table": "premises", "column": "address", "op": "blank"}}
```

    -> count_rows({"table": "premises", "column": "address", "op": "blank"})

## step 4

```json
{"tool": "record_finding", "args": {"title": "Two rows in the premises table have blank address values, violating the requirement that address must never be blank.", "evidence_tool": "count_rows", "evidence_args": {"table": "premises", "column": "address", "op": "blank"}, "expected": "0"}}
```

    -> record_finding({"title": "Two rows in the premises table have blank address values, violating the requirement that address must never be blank.", "evidence_tool": "count_rows", "evidence_args": {"table": "premises", "column": "address", "op": "blank"}, "expected": "0"})

## step 5

```json
{"tool": "count_rows", "args": {"table": "premises", "column": "address", "op": "blank"}}
```

    -> count_rows({"table": "premises", "column": "address", "op": "blank"})

## step 6

```json
{"tool": "record_finding", "args": {"title": "Two rows in the premises table have blank address values, violating the requirement that address must never be blank.", "evidence_tool": "count_rows", "evidence_args": {"table": "premises", "column": "address", "op": "blank"}, "expected": "2"}}
```

    -> record_finding({"title": "Two rows in the premises table have blank address values, violating the requirement that address must never be blank.", "evidence_tool": "count_rows", "evidence_args": {"table": "premises", "column": "address", "op": "blank"}, "expected": "2"})

## step 7

```json
{"tool": "finish", "args": {"summary": "Found 2 rows in the premises table with blank address values, which violates the requirement that address must never be blank."}}
```

    -> finish({"summary": "Found 2 rows in the premises table with blank address values, which violates the requirement that address must never be blank."})
