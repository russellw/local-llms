# basics -- Find the impossible values in a numeric column

target hit: True   stopped: finish   steps: 6/8   tools: list_tables, describe_table, sample_column, count_rows, record_finding, finish

## step 1

    -> list_tables({})

## step 2

    -> describe_table({"table": "readings"})

## step 3

    -> sample_column({"table": "readings", "column": "kwh", "n": "5"})

## step 4

    -> count_rows({"table": "readings", "column": "kwh", "op": "<", "value": "0"})

## step 5

    -> record_finding({"title": "The kwh column in the readings table contains 3 rows with negative values, violating the expectation that consumption readings cannot be negative.", "evidence_tool": "count_rows", "evidence_args": "{\"table\": \"readings\", \"column\": \"kwh\", \"op\": \"<\", \"value\": \"0\"}", "expected": "3"})

## step 6

    -> finish({"summary": "I found that the kwh column in the readings table contains 3 rows with negative values, which violates the expectation that consumption readings cannot be negative. This was confirmed by counting rows where kwh is less than 0."})
