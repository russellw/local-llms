# shapes -- Count blank values in a column you can only sample

target hit: False   stopped: finish   steps: 4/8   tools: count_rows, describe_table, finish

## step 1

```json
{"tool": "count_rows", "args": {"table": "readings", "column": "premises.address", "op": "blank"}}
```

    -> count_rows({"table": "readings", "column": "premises.address", "op": "blank"})

## step 2

```json
{"tool": "describe_table", "args": {"table": "readings"}}
```

    -> describe_table({"table": "readings"})

## step 3

```json
{"tool": "count_rows", "args": {"table": "readings", "column": "premises.address", "op": "blank"}}
```

    -> count_rows({"table": "readings", "column": "premises.address", "op": "blank"})

## step 4

```json
{"tool": "finish", "summary": "There are no rows in the 'readings' table where 'premises.address' is blank."}
```

    -> finish({"summary": "There are no rows in the 'readings' table where 'premises.address' is blank."})
