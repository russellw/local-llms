# basics -- Find the impossible values in a numeric column

target hit: True   stopped: finish   steps: 5/8   tools: list_tables, describe_table, count_rows, record_finding, finish

## step 1

    -> list_tables({})

## step 2

    -> describe_table({"table": "readings"})

## step 3

    -> count_rows({"table": "readings", "column": "kwh", "op": "<", "value": "0"})

## step 4

    -> record_finding({"title": "Negative kwh readings", "evidence_tool": "count_rows", "evidence_args": "{\"table\":\"readings\",\"column\":\"kwh\",\"op\":\"<\",\"value\":\"0\"}", "expected": "3"})

## step 5

    -> finish({"summary": "Found three readings with negative kwh values, violating the non\u2011negative consumption rule."})
